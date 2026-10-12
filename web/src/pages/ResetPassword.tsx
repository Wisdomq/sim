import {
  Alert,
  Button,
  Center,
  Group,
  Paper,
  PasswordInput,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { IconAlertCircle, IconCheck, IconLock } from '@tabler/icons-react'
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, errorMessage } from '../lib/api'

export default function ResetPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [busy, setBusy] = useState(false)
  const [validating, setValidating] = useState(true)
  const [tokenValid, setTokenValid] = useState(false)

  useEffect(() => {
    async function validateToken() {
      if (!token) {
        setError('Invalid reset link. No token provided.')
        setValidating(false)
        return
      }

      try {
        const response = await api.post('/auth/validate-reset-token', { token })
        setTokenValid(response.data.valid)
        if (!response.data.valid) {
          setError('This reset link is invalid or has expired.')
        }
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setValidating(false)
      }
    }

    validateToken()
  }, [token])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (!token) {
      setError('Invalid reset link. No token provided.')
      return
    }

    setBusy(true)
    setError(null)
    try {
      await api.post('/auth/reset-password', {
        token,
        new_password: password,
      })
      setSuccess(true)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (validating) {
    return (
      <Center h="100vh" bg="gray.0">
        <Paper shadow="md" p="xl" radius="md" w={400} withBorder>
          <Stack gap="md">
            <Text c="dimmed">Validating reset link...</Text>
          </Stack>
        </Paper>
      </Center>
    )
  }

  if (!tokenValid) {
    return (
      <Center h="100vh" bg="gray.0">
        <Paper shadow="md" p="xl" radius="md" w={400} withBorder>
          <Stack gap="md">
            <Alert color="red" icon={<IconAlertCircle size={16} />}>
              {error || 'This reset link is invalid or has expired.'}
            </Alert>
            <Group justify="flex-end">
              <Button onClick={() => navigate('/forgot-password')}>
                Request new link
              </Button>
            </Group>
          </Stack>
        </Paper>
      </Center>
    )
  }

  if (success) {
    return (
      <Center h="100vh" bg="gray.0">
        <Paper shadow="md" p="xl" radius="md" w={400} withBorder>
          <Stack gap="md">
            <Alert color="green" icon={<IconCheck size={16} />}>
              Password has been reset successfully. You can now sign in with your new password.
            </Alert>
            <Group justify="flex-end">
              <Button onClick={() => navigate('/login')}>Sign in</Button>
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
              <Title order={2}>Set new password</Title>
              <Text c="dimmed" size="sm">
                Enter your new password below.
              </Text>
            </div>
            <PasswordInput
              label="New password"
              placeholder="••••••••"
              leftSection={<IconLock size={16} />}
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
              autoComplete="new-password"
              minLength={8}
            />
            <PasswordInput
              label="Confirm password"
              placeholder="••••••••"
              leftSection={<IconLock size={16} />}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.currentTarget.value)}
              required
              autoComplete="new-password"
              minLength={8}
            />
            {error && (
              <Alert color="red" icon={<IconAlertCircle size={16} />}>
                {error}
              </Alert>
            )}
            <Group justify="flex-end">
              <Button type="submit" loading={busy}>
                Reset password
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Center>
  )
}
