import {
  Alert,
  Anchor,
  Button,
  Center,
  Group,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { IconAlertCircle, IconMail } from '@tabler/icons-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../lib/api'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.post('/auth/forgot-password', { email: email.trim() })
      setSuccess(true)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (success) {
    return (
      <Center h="100vh" bg="gray.0">
        <Paper shadow="md" p="xl" radius="md" w={400} withBorder>
          <Stack gap="md">
            <div>
              <Title order={2}>Check your email</Title>
              <Text c="dimmed" size="sm">
                If an account exists for {email}, we've sent a password reset link.
              </Text>
            </div>
            <Group justify="flex-end">
              <Button onClick={() => navigate('/login')}>Back to login</Button>
            </Group>
          </Stack>
        </Paper>
      </Center>
    )
  }

  return (
    <Center h="100vh" bg="gray.0">
      <Paper shadow="md" p="xl" radius="md" w={400} withBorder>
        <form onSubmit={onSubmit}>
          <Stack gap="md">
            <div>
              <Title order={2}>Reset your password</Title>
              <Text c="dimmed" size="sm">
                Enter your email address and we'll send you a reset link.
              </Text>
            </div>
            <TextInput
              label="Email"
              placeholder="hq@example.com"
              leftSection={<IconMail size={16} />}
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              required
              autoComplete="email"
            />
            {error && (
              <Alert color="red" icon={<IconAlertCircle size={16} />}>
                {error}
              </Alert>
            )}
            <Group justify="space-between">
              <Anchor size="sm" onClick={() => navigate('/login')}>
                Back to login
              </Anchor>
              <Button type="submit" loading={busy}>
                Send reset link
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Center>
  )
}
