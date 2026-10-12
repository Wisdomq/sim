import { createBrowserRouter } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import RequireHQ from './components/RequireHQ'
import Dashboard from './pages/Dashboard'
import Denied from './pages/Denied'
import ForgotPassword from './pages/ForgotPassword'
import Login from './pages/Login'
import Management from './pages/Management'
import Reconciliation from './pages/Reconciliation'
import ResetPassword from './pages/ResetPassword'
import Stock from './pages/Stock'

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  { path: '/forgot-password', element: <ForgotPassword /> },
  { path: '/reset-password', element: <ResetPassword /> },
  { path: '/denied', element: <Denied /> },
  {
    element: <RequireHQ />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { index: true, element: <Dashboard /> },
          { path: 'stock', element: <Stock /> },
          { path: 'reconciliation', element: <Reconciliation /> },
          { path: 'management', element: <Management /> },
        ],
      },
    ],
  },
])