// Read-only browser verification of this local app. Credentials never printed.
const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
async function main(){
  const root=path.resolve(__dirname,'..');
  const owner=JSON.parse(fs.readFileSync(path.join(root,'local-state/sso-realm.json'),'utf8')).users[0];
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1120}});
    await page.goto('http://127.0.0.1:13000/');
    await page.getByRole('link',{name:'Sign in with Southern Shade SSO'}).click();
    await page.getByRole('textbox',{name:'Username or email'}).fill(owner.username);
    await page.getByRole('textbox',{name:'Password',exact:true}).fill(owner.credentials[0].value);
    await page.getByRole('button',{name:'Sign In',exact:true}).click();
    await page.getByRole('heading',{name:'Workflows',exact:true}).first().waitFor();
    await page.getByText('Control plane operational',{exact:true}).waitFor();
    await page.screenshot({path:path.join(root,'local-state/console-desktop.png'),fullPage:true});
    await page.getByRole('textbox',{name:'Filter records'}).fill('no-record-should-match-this');
    if(await page.locator('tbody tr').count())throw new Error('Search did not filter records');
    await page.getByRole('textbox',{name:'Filter records'}).fill('');
    await page.getByRole('button',{name:'Orchestration runs',exact:true}).click();
    await page.getByRole('button',{name:'View timeline'}).first().click();
    await page.getByRole('heading',{name:'Run timeline',exact:true}).waitFor();
    await page.screenshot({path:path.join(root,'local-state/console-evidence.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.getByRole('button',{name:'Workflows',exact:true}).click();
    await page.screenshot({path:path.join(root,'local-state/console-mobile.png'),fullPage:true});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
    if(overflow){console.log(await page.evaluate(()=>Array.from(document.querySelectorAll('body *')).filter(el=>el.getBoundingClientRect().right>innerWidth+1).map(el=>({tag:el.tagName,class:el.className,right:el.getBoundingClientRect().right})).slice(0,20)));throw new Error('Mobile page overflow');}
    console.log('PASS: browser SSO, desktop dashboard, filtering, run timeline, mobile layout');
  }finally{await browser.close();}
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
