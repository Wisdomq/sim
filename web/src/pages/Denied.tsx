import { Button, Center, Stack, Text, Title } from '@mantine/core'
import { IconDeviceMobile } from '@tabler/icons-react'
import { useAuth } from '../lib/auth'

export default function Denied() {
  const { logout, user } = useAuth()
  return (
    <Center h="100vh" bg="gray.0">
      <Stack align="center" gap="sm" w={440}>
        <IconDeviceMobile size={56} stroke={1.5} color="var(--mantine-color-gray-5)" />
        <Title order={2}>HQ access only</Title>
        <Text c="dimmed" ta="center">
          {user?.role === 'BA'
            ? 'Brand Ambassador accounts can only use the mobile app.'
            : 'Branch accounts can only use the mobile app.'}
          <br />
          Sign in with an HQ account to use this portal.
        </Text>
        <Button variant="outline" onClick={logout}>
          Sign in with a different account
        </Button>
      </Stack>
    </Center>
  )
}