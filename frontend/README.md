# R.A.E. Control Plane - Frontend Dashboard

Next.js 15 dashboard for the R.A.E. Control Plane's enterprise-grade AI governance system. Provides real-time visibility and control for Registry, Controls, and Enforcement layers with Microsoft Entra ID (Azure AD) SSO.

## Architecture

### Tech Stack
- **Framework**: Next.js 15 (App Router, React Server Components)
- **UI**: Tailwind CSS enterprise design system
- **Auth**: MSAL.js 3.0 (Microsoft Entra ID browser-based SSO)
- **State**: React Context API for auth state management
- **API Client**: Axios with interceptors for JWT token refresh
- **Type Safety**: TypeScript with strict mode

### Directory Structure
```
frontend/
├── app/                        # Next.js 15 App Router
│   ├── layout.tsx             # Root layout with MSAL provider
│   ├── page.tsx               # Dashboard homepage
│   └── globals.css            # Tailwind directives
├── components/
│   └── providers/
│       └── MsalProvider.tsx   # Entra ID auth wrapper (SSR-safe)
├── lib/
│   └── api.ts                 # Axios client (JWT bearer tokens)
├── .env.example               # Environment variables template
├── next.config.js             # API proxy + security headers
├── package.json               # Dependencies (Next.js 15, MSAL 3.0)
├── tailwind.config.js         # Enterprise color palette
└── tsconfig.json              # Strict TypeScript config
```

## Prerequisites

### Required Services
1. **Backend API**: R.A.E. Control Plane FastAPI service running
2. **Azure Entra ID**: Application registration with OAuth 2.0
3. **Node.js**: Version 20.x or 22.x (LTS)
4. **Database**: PostgreSQL backend (accessed via API)

### Azure App Registration Setup
1. Navigate to [Azure Portal](https://portal.azure.com) → Microsoft Entra ID → App registrations
2. Create new registration:
   - Name: `R.A.E. Control Plane Dashboard`
   - Supported account types: Single tenant
   - Redirect URI: `http://localhost:3000` (development)
3. Copy Application (client) ID → use as `NEXT_PUBLIC_MSAL_CLIENT_ID`
4. Add API permissions:
   - Microsoft Graph: `User.Read` (delegated)
5. Authentication → Enable PKCE flow (default for SPAs)

## Installation

### 1. Environment Configuration
```bash
cp .env.example .env.local
```

Edit `.env.local` with your values:
```bash
# Azure Entra ID OAuth 2.0 (from app registration)
NEXT_PUBLIC_MSAL_CLIENT_ID=your-azure-client-id-here
NEXT_PUBLIC_MSAL_TENANT_ID=your-tenant-id-or-common
NEXT_PUBLIC_MSAL_REDIRECT_URI=http://localhost:3000

# Backend API endpoint (FastAPI service)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# Optional: Analytics (comment out if not using)
# NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
# NEXT_PUBLIC_SENTRY_DSN=your-sentry-dsn
```

### 2. Install Dependencies
```bash
npm install
# or
yarn install
# or
pnpm install
```

### 3. Run Development Server
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Development Workflow

### Authentication Flow
1. User accesses dashboard → MSAL detects no auth token
2. Redirect to Microsoft login page (Entra ID)
3. User authenticates → Entra ID returns authorization code
4. MSAL exchanges code for access token (PKCE flow)
5. Token stored in browser `localStorage` (persistent across refreshes)
6. API requests include token as `Authorization: Bearer <token>`

### API Integration Pattern
```typescript
// lib/api.ts - Axios instance with auto-token injection
import axios from 'axios';
import { msalInstance } from '@/components/providers/MsalProvider';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
});

apiClient.interceptors.request.use(async (config) => {
  const account = msalInstance.getActiveAccount();
  if (account) {
    const response = await msalInstance.acquireTokenSilent({
      scopes: ['api://your-backend-app-id/access_as_user'],
      account,
    });
    config.headers.Authorization = `Bearer ${response.accessToken}`;
  }
  return config;
});
```

### Component Development
- **Server Components**: Use for static layouts and data fetching (default)
- **Client Components**: Mark with `'use client'` for interactive UI (forms, modals)
- **MSAL Usage**: Only in client components (browser-only library)

### Type Safety
```bash
# Check types without building
npm run type-check
```

## Production Build

### Build Process
```bash
npm run build
```

This generates:
- Optimized static pages (`.next/static`)
- Server-side rendered pages (`.next/server`)
- Type-checked components
- Minified CSS bundles

### Environment Variables for Production
Update `.env.production`:
```bash
NEXT_PUBLIC_MSAL_REDIRECT_URI=https://your-production-domain.com
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com/api/v1
```

### Deployment Options
1. **Vercel** (recommended for Next.js):
   ```bash
   npm install -g vercel
   vercel --prod
   ```
   - Auto-configures Next.js optimizations
   - Environment variables via dashboard

2. **Docker**:
   ```dockerfile
   FROM node:20-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci --only=production
   COPY . .
   RUN npm run build
   EXPOSE 3000
   CMD ["npm", "start"]
   ```

3. **AWS/GCP**: Use Terraform + ECS/Cloud Run with Next.js standalone output

### Update Azure Redirect URI
Add production domain to app registration:
- Azure Portal → App registrations → Authentication → Add URI:
  `https://your-production-domain.com`

## Security Considerations

### Token Storage
- **Access tokens**: Stored in memory (MSAL handles securely)
- **Refresh tokens**: httpOnly cookies (if using backend proxy)
- **Never expose**: Client secrets in frontend code

### Content Security Policy
Configured in `next.config.js`:
```javascript
module.exports = {
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: "default-src 'self'; script-src 'self' 'unsafe-eval'; connect-src 'self' https://login.microsoftonline.com;"
          },
        ],
      },
    ];
  },
};
```

### API Security
- All backend requests require valid JWT tokens
- CORS configured in FastAPI to allow only frontend origin
- Rate limiting handled by backend enforcement gates

## Compliance Mapping

### NIST AI RMF Functions
- **GOVERN**: Dashboard provides visibility into control policies and enforcement status
- **MAP**: Registry visualization (workflows, capabilities, connectors)
- **MEASURE**: Real-time audit event streaming and kill-switch status
- **MANAGE**: Break-glass activation UI and change request workflows

### Audit Trail Integration
- All user actions logged via backend API
- SHA-256 hash-chained audit events displayed in timeline view
- Tamper-evident log verification UI

## Troubleshooting

### MSAL Login Redirect Loop
**Symptom**: Infinite redirects to Microsoft login
**Solution**:
1. Clear browser `localStorage` (includes MSAL cache)
2. Verify `NEXT_PUBLIC_MSAL_REDIRECT_URI` matches Azure app registration exactly
3. Check browser console for CORS errors

### API 401 Unauthorized
**Symptom**: Dashboard loads but API calls fail
**Solution**:
1. Verify backend is running and accepting CORS from `http://localhost:3000`
2. Check token expiration (MSAL auto-refreshes if configured)
3. Ensure backend validates Entra ID tokens (audience claim must match)

### Build Errors
**Symptom**: TypeScript errors during `npm run build`
**Solution**:
```bash
npm run type-check  # Identify specific errors
rm -rf .next node_modules  # Clear cache
npm install
```

## Development Roadmap

### Phase 8: API Integration (Next Steps)
- [ ] Create `lib/api.ts` Axios client with token interceptors
- [ ] Implement Registry dashboard page (`app/registry/page.tsx`)
- [ ] Build Controls visualization components
- [ ] Add Enforcement audit log timeline
- [ ] Create ChangeRequest approval workflow UI

### Phase 9: Production Hardening
- [ ] Add error boundaries for client components
- [ ] Implement retry logic for failed API calls
- [ ] Set up monitoring (Sentry integration)
- [ ] E2E tests with Playwright
- [ ] Accessibility audit (WCAG 2.1 AA compliance)

## License
MIT License - See root LICENSE file

## Support
For issues related to:
- **Azure/Entra ID**: Check [MSAL.js documentation](https://github.com/AzureAD/microsoft-authentication-library-for-js)
- **Next.js**: [Next.js docs](https://nextjs.org/docs)
- **Backend API**: See `backend/README.md`

---

**Last Updated**: Phase 7 (Frontend Infrastructure)
**Next Phase**: Phase 8 (API Integration + Dashboard Components)
