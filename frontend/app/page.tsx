export default function HomePage() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            R.A.E. Control Plane
          </h1>
          <p className="text-lg text-gray-600">
            Enterprise AI Governance Dashboard - NIST AI RMF Aligned
          </p>
        </header>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Registry Card */}
          <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 mb-3">
              Registry
            </h2>
            <p className="text-gray-600 mb-4">
              Manage workflows, capabilities, and connectors
            </p>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Workflows</span>
                <span className="text-sm font-medium text-primary-600">-</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Capabilities</span>
                <span className="text-sm font-medium text-primary-600">-</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Connectors</span>
                <span className="text-sm font-medium text-primary-600">-</span>
              </div>
            </div>
          </div>

          {/* Controls Card */}
          <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 mb-3">
              Controls
            </h2>
            <p className="text-gray-600 mb-4">
              Kill switches, policies, and break-glass access
            </p>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Kill Switches</span>
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-success-50 text-success-700">ACTIVE</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Control Policies</span>
                <span className="text-sm font-medium text-primary-600">-</span>
              </div>
            </div>
          </div>

          {/* Enforcement Card */}
          <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 mb-3">
              Enforcement
            </h2>
            <p className="text-gray-600 mb-4">
              Audit logs, gates, and change requests
            </p>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Audit Events</span>
                <span className="text-sm font-medium text-primary-600">-</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Change Requests</span>
                <span className="text-sm font-medium text-primary-600">-</span>
              </div>
            </div>
          </div>
        </div>

        {/* Business Evaluator Card */}
        <div className="bg-white rounded-lg shadow-md p-6 border border-blue-200 bg-blue-50">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">
            Business Deal Evaluator
          </h2>
          <p className="text-gray-600 mb-4">
            Enter a listing's financials to score the deal — multiples, DSCR, payback period, and an A–F grade.
          </p>
          <a
            href="/business-eval"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 transition-colors"
          >
            Open Evaluator →
          </a>
        </div>

        {/* Compliance Footer */}
        <footer className="mt-8 pt-6 border-t border-gray-200">
          <div className="flex flex-wrap gap-4 text-sm text-gray-500">
            <span className="inline-flex items-center">
              <span className="w-2 h-2 rounded-full bg-success-500 mr-2"></span>
              NIST AI RMF
            </span>
            <span className="inline-flex items-center">
              <span className="w-2 h-2 rounded-full bg-success-500 mr-2"></span>
              SOC 2 Type II
            </span>
            <span className="inline-flex items-center">
              <span className="w-2 h-2 rounded-full bg-success-500 mr-2"></span>
              HIPAA
            </span>
            <span className="inline-flex items-center">
              <span className="w-2 h-2 rounded-full bg-success-500 mr-2"></span>
              ISO 27001
            </span>
          </div>
        </footer>
      </div>
    </main>
  );
}
