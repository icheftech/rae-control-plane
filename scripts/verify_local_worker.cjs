// Verify the real local worker queue through the browser. No credentials printed.
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
async function main(){
  const root=path.resolve(__dirname,'..');
  const owner=JSON.parse(fs.readFileSync(path.join(root,'local-state/sso-realm.json'),'utf8')).users[0];
  const demo=JSON.parse(fs.readFileSync(path.join(root,'local-state/worker-demo-results.json'),'utf8'));
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1120}});
    await page.goto('http://127.0.0.1:13000/');
    await page.getByRole('link',{name:'Sign in with Southern Shade SSO'}).click();
    await page.getByRole('textbox',{name:'Username or email'}).fill(owner.username);
    await page.getByRole('textbox',{name:'Password',exact:true}).fill(owner.credentials[0].value);
    await page.getByRole('button',{name:'Sign In',exact:true}).click();
    await page.getByRole('button',{name:'Orchestration runs',exact:true}).click();
    await page.getByText('Worker connected',{exact:true}).waitFor();
    await page.getByRole('combobox',{name:'Workflow',exact:true}).selectOption(demo.workflow_id);
    await page.getByRole('textbox',{name:'Installed task key'}).fill(demo.task_key);
    await page.getByRole('button',{name:'Queue local job',exact:true}).click();
    const notice=page.getByRole('status').filter({hasText:/Job .* queued/});
    await notice.waitFor();
    const id=(await notice.textContent()).match(/Job ([a-f0-9]{8})/)[1];
    const row=page.getByRole('row').filter({hasText:id});
    await row.getByText('success',{exact:true}).waitFor({timeout:20000});
    const interrupted=page.getByRole('row').filter({hasText:demo.interrupted_job.slice(0,8)});
    await interrupted.getByText('interrupted',{exact:true}).waitFor();
    await interrupted.getByRole('button',{name:'View run evidence'}).click();
    await page.getByRole('heading',{name:'Run timeline',exact:true}).waitFor();
    await page.screenshot({path:path.join(root,'local-state/worker-desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.join(root,'local-state/worker-mobile.png'),fullPage:true});
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile overflow');
    console.log('PASS: worker connected, browser submission, job completion, interrupted evidence, responsive layout');
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
