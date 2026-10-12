import { Center, Loader } from '@mantine/core'
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import Denied from '../pages/Denied'

export default function RequireHQ() {
  const { status, user } = useAuth()

  if (status === 'loading') {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    )
  }
  if (status === 'anonymous') {
    return <Navigate to="/login" replace />
  }
  if (user?.role !== 'HQ') {
    return <Denied />
  }
  return <Outlet />
}