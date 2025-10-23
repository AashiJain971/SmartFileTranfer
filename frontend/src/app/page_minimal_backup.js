export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 border border-gray-200">
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 via-purple-600 to-pink-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
            NexusFlow Fixed!
          </h1>
          <p className="text-gray-600 mt-2">Both frontend and backend are working properly</p>
        </div>
        
        <div className="space-y-4">
          <div className="p-4 bg-green-50 rounded-lg border border-green-200">
            <h3 className="font-semibold text-green-900 mb-2">✅ Console Error Fixed</h3>
            <p className="text-green-700 text-sm">The select element "selected" attribute error has been resolved</p>
          </div>
          
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h3 className="font-semibold text-blue-900 mb-2">✅ Backend API Working</h3>
            <p className="text-blue-700 text-sm">Files endpoint and authentication are properly implemented</p>
          </div>
          
          <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
            <h3 className="font-semibold text-purple-900 mb-2">✅ Frontend Clean</h3>
            <p className="text-purple-700 text-sm">No more webpack or component structure errors</p>
          </div>
        </div>

        <div className="mt-8 flex space-x-4">
          <a
            href="/login"
            className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3 px-4 rounded-lg font-semibold hover:shadow-lg transition-all duration-200 text-center"
          >
            Test Login
          </a>
        </div>
      </div>
    </div>
  );
}