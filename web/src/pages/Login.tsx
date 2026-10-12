import {
  Alert,
  Anchor,
  Button,
  Center,
  Group,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { IconAlertCircle, IconLock, IconUser } from '@tabler/icons-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { errorMessage } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function Login() {
  const navigate = useNavigate()
  const { login, status } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const user = await login(email.trim(), password)
      navigate(user.role === 'HQ' ? '/' : '/denied', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Center h="100vh" bg="gray.0">
      <Paper shadow="md" p="xl" radius="md" w={400} withBorder>
        <form onSubmit={onSubmit}>
          <Stack gap="md">
            <div>
              <Title order={2}>SIM Stock &amp; Sales</Title>
              <Text c="dimmed" size="sm">
                HQ portal — sign in to continue
              </Text>
            </div>
            {status === 'loading' && (
              <Text size="sm" c="dimmed">
                Restoring session…
              </Text>
            )}
            <TextInput
              label="Email"
              placeholder="hq@example.com"
              leftSection={<IconUser size={16} />}
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              required
              autoComplete="username"
            />
            <PasswordInput
              label="Password"
              placeholder="••••••••"
              leftSection={<IconLock size={16} />}
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
              autoComplete="current-password"
            />
            <Group justify="flex-end">
              <Anchor size="sm" onClick={() => navigate('/forgot-password')}>
                Forgot password?
              </Anchor>
            </Group>
            {error && (
              <Alert color="red" icon={<IconAlertCircle size={16} />}>
                {error}
              </Alert>
            )}
            <Group justify="flex-end">
              <Button type="submit" loading={busy} disabled={status === 'loading'}>
                Sign in
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Center>
  )
}