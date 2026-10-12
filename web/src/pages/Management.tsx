import {
  Alert,
  Badge,
  Button,
  Card,
  FileInput,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import { IconAlertCircle, IconTrash } from '@tabler/icons-react'
import { useState } from 'react'
import { errorMessage } from '../lib/api'
import {
  toLocalIso,
  uploadPhoto,
  useBrandAmbassadors,
  useBranches,
  useCommissionRules,
  useCreateBA,
  useCreateBranch,
  useCreateCommissionRule,
  useCreateTarget,
  useDeleteBA,
  useDeleteBranch,
  useFlagActions,
  useFlags,
  useMarkNotificationRead,
  useNotifications,
  useTargets,
  type BranchType,
} from '../lib/hq'

async function uploadAndGetUrl(
  file: File | null,
  setBusy: (b: boolean) => void,
  setError: (e: string | null) => void,
): Promise<string> {
  if (!file) {
    setError('Please attach a photo (PNG/JPEG/WebP).')
    throw new Error('no-photo')
  }
  setBusy(true)
  setError(null)
  try {
    const { photo_url } = await uploadPhoto(file)
    return photo_url
  } catch (err) {
    setError(errorMessage(err))
    throw err
  } finally {
    setBusy(false)
  }
}

function PhotoStep({
  file,
  setFile,
  photoUrl,
}: {
  file: File | null
  setFile: (f: File | null) => void
  photoUrl: string | null
}) {
  return (
    <>
      <FileInput
        label="ID photo"
        placeholder="PNG/JPEG/WebP"
        accept="image/png,image/jpeg,image/webp"
        value={file}
        onChange={setFile}
        clearable
      />
      {photoUrl && (
        <Text size="xs" c="dimmed">
          Photo staged for upload: {photoUrl.split('/').pop()}
        </Text>
      )}
    </>
  )
}

function Branches() {
  const branches = useBranches()
  const createBranch = useCreateBranch()
  const deleteBranch = useDeleteBranch()
  const [opened, { open, close }] = useDisclosure()
  const [form, setForm] = useState({
    name: '',
    type: 'SHOP' as BranchType,
    id_number: '',
    email: '',
    password: '',
  })
  const [file, setFile] = useState<File | null>(null)
  const [photoUrl, setPhotoUrl] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    let url = photoUrl
    if (!url) {
      try {
        url = await uploadAndGetUrl(file, setBusy, setError)
      } catch {
        return
      }
    }
    setBusy(true)
    try {
      await createBranch.mutateAsync({ ...form, photo_url: url })
      notifications.show({ title: 'Branch created', message: `${form.name}.` })
      close()
      setForm({ name: '', type: 'SHOP', id_number: '', email: '', password: '' })
      setFile(null)
      setPhotoUrl(null)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card shadow="sm" radius="md" withBorder>
      <Group justify="space-between" mb="sm">
        <Title order={5}>Branches</Title>
        <Button onClick={open}>New branch</Button>
      </Group>
      {branches.isLoading ? (
        <Loader />
      ) : (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>ID number</Table.Th>
              <Table.Th>Created</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(branches.data ?? []).map((b) => (
              <Table.Tr key={b.id}>
                <Table.Td>{b.name}</Table.Td>
                <Table.Td>
                  <Badge variant="light">{b.type}</Badge>
                </Table.Td>
                <Table.Td>{b.id_number}</Table.Td>
                <Table.Td>{new Date(b.created_at).toLocaleDateString()}</Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    color="red"
                    variant="subtle"
                    leftSection={<IconTrash size={14} />}
                    onClick={async () => {
                      if (!window.confirm(`Remove branch "${b.name}"?`)) return
                      try {
                        await deleteBranch.mutateAsync(b.id)
                        notifications.show({ title: 'Branch removed', message: `Branch #${b.id}.` })
                      } catch (err) {
                        notifications.show({
                          color: 'red',
                          title: 'Remove failed',
                          message: errorMessage(err),
                        })
                      }
                    }}
                  >
                    Remove
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={opened} onClose={close} title="New branch account">
        <form onSubmit={onSubmit}>
          <Stack gap="sm">
            <TextInput
              label="Branch name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
              required
            />
            <Select
              label="Type"
              data={[
                { value: 'SHOP', label: 'Shop' },
                { value: 'VAN', label: 'Van' },
              ]}
              value={form.type}
              onChange={(v) => setForm({ ...form, type: (v ?? 'SHOP') as BranchType })}
            />
            <TextInput
              label="ID number"
              value={form.id_number}
              onChange={(e) => setForm({ ...form, id_number: e.currentTarget.value })}
              required
            />
            <TextInput
              label="Email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.currentTarget.value })}
              required
            />
            <TextInput
              label="Password"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.currentTarget.value })}
              required
            />
            <PhotoStep file={file} setFile={setFile} photoUrl={photoUrl} />
            {error && (
              <Alert color="red" icon={<IconAlertCircle size={16} />}>
                {error}
              </Alert>
            )}
            <Group justify="flex-end">
              <Button type="submit" loading={busy}>
                Create branch
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Card>
  )
}

function Ambassadors() {
  const branches = useBranches()
  const [branchFilter, setBranchFilter] = useState<string | null>(null)
  const ambassadors = useBrandAmbassadors(branchFilter ? Number(branchFilter) : null)
  const createBA = useCreateBA()
  const deleteBA = useDeleteBA()
  const [opened, { open, close }] = useDisclosure()
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    phone_msisdn: '',
    id_number: '',
  })
  const [file, setFile] = useState<File | null>(null)
  const [photoUrl, setPhotoUrl] = useState<string | null>(null)
  const [targetBranch, setTargetBranch] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!targetBranch) return
    setError(null)
    let url = photoUrl
    if (!url) {
      try {
        url = await uploadAndGetUrl(file, setBusy, setError)
      } catch {
        return
      }
    }
    setBusy(true)
    try {
      await createBA.mutateAsync({
        branchId: Number(targetBranch),
        name: form.name,
        email: form.email,
        password: form.password,
        phone_msisdn: form.phone_msisdn || undefined,
        id_number: form.id_number,
        photo_url: url,
      })
      notifications.show({ title: 'Brand ambassador created', message: form.name })
      close()
      setForm({ name: '', email: '', password: '', phone_msisdn: '', id_number: '' })
      setFile(null)
      setPhotoUrl(null)
      setTargetBranch(null)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card shadow="sm" radius="md" withBorder>
      <Group justify="space-between" mb="sm">
        <Title order={5}>Brand ambassadors</Title>
        <Group gap="xs">
          <Select
            placeholder="Filter by branch"
            clearable
            searchable
            data={(branches.data ?? []).map((b) => ({ value: String(b.id), label: b.name }))}
            value={branchFilter}
            onChange={setBranchFilter}
            w={240}
          />
          <Button onClick={open}>New BA</Button>
        </Group>
      </Group>
      {ambassadors.isLoading ? (
        <Loader />
      ) : (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Branch</Table.Th>
              <Table.Th>Phone</Table.Th>
              <Table.Th>ID number</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(ambassadors.data ?? []).map((ba) => (
              <Table.Tr key={ba.id}>
                <Table.Td>{ba.name}</Table.Td>
                <Table.Td>{branches.data?.find((b) => b.id === ba.branch_id)?.name ?? ba.branch_id}</Table.Td>
                <Table.Td>{ba.phone_msisdn ?? '—'}</Table.Td>
                <Table.Td>{ba.id_number}</Table.Td>
                <Table.Td>
                  <Badge color={ba.status === 'ACTIVE' ? 'teal' : 'red'} variant="light">
                    {ba.status}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    color="red"
                    variant="subtle"
                    leftSection={<IconTrash size={14} />}
                    onClick={async () => {
                      if (!window.confirm(`Remove ${ba.name}?`)) return
                      try {
                        await deleteBA.mutateAsync(ba.id)
                        notifications.show({ title: 'Ambassador removed', message: `Ambassador #${ba.id}.` })
                      } catch (err) {
                        notifications.show({
                          color: 'red',
                          title: 'Remove failed',
                          message: errorMessage(err),
                        })
                      }
                    }}
                  >
                    Remove
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
            {(ambassadors.data ?? []).length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text size="sm" c="dimmed" ta="center">
                    No brand ambassadors yet.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={opened} onClose={close} title="New brand ambassador">
        <form onSubmit={onSubmit}>
          <Stack gap="sm">
            <Select
              label="Branch"
              placeholder="Select branch"
              searchable
              data={(branches.data ?? []).map((b) => ({ value: String(b.id), label: b.name }))}
              value={targetBranch}
              onChange={setTargetBranch}
              required
            />
            <TextInput
              label="Full name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.currentTarget.value })}
              required
            />
            <TextInput
              label="Email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.currentTarget.value })}
              required
            />
            <TextInput
              label="Password"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.currentTarget.value })}
              required
            />
            <TextInput
              label="Phone (MSISDN)"
              value={form.phone_msisdn}
              onChange={(e) => setForm({ ...form, phone_msisdn: e.currentTarget.value })}
            />
            <TextInput
              label="ID number"
              value={form.id_number}
              onChange={(e) => setForm({ ...form, id_number: e.currentTarget.value })}
              required
            />
            <PhotoStep file={file} setFile={setFile} photoUrl={photoUrl} />
            {error && (
              <Alert color="red" icon={<IconAlertCircle size={16} />}>
                {error}
              </Alert>
            )}
            <Group justify="flex-end">
              <Button type="submit" loading={busy}>
                Create BA
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Card>
  )
}

function Commission() {
  const rules = useCommissionRules()
  const targets = useTargets()
  const branches = useBranches()
  const createRule = useCreateCommissionRule()
  const createTarget = useCreateTarget()
  const [ruleOpen, { open: openRule, close: closeRule }] = useDisclosure()
  const [targetOpen, { open: openTarget, close: closeTarget }] = useDisclosure()
  const [ruleForm, setRuleForm] = useState({
    name: '',
    amount_per_sim: '10',
    effective_from: '',
    effective_to: '',
  })
  const [targetForm, setTargetForm] = useState({
    branch_id: '',
    period_type: 'DAILY',
    quantity: 10,
    effective_from: '',
    effective_to: '',
  })
  const [error, setError] = useState<string | null>(null)

  async function submitRule(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await createRule.mutateAsync({
        name: ruleForm.name,
        amount_per_sim: ruleForm.amount_per_sim,
        effective_from: toLocalIso(ruleForm.effective_from),
        effective_to: ruleForm.effective_to ? toLocalIso(ruleForm.effective_to) : undefined,
      })
      notifications.show({ title: 'Commission rule created', message: ruleForm.name })
      closeRule()
      setRuleForm({ name: '', amount_per_sim: '10', effective_from: '', effective_to: '' })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  async function submitTarget(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!targetForm.branch_id) return
    try {
      await createTarget.mutateAsync({
        branch_id: Number(targetForm.branch_id),
        period_type: targetForm.period_type,
        quantity: targetForm.quantity,
        effective_from: toLocalIso(targetForm.effective_from),
        effective_to: targetForm.effective_to ? toLocalIso(targetForm.effective_to) : undefined,
      })
      notifications.show({ title: 'Branch target created', message: 'Target saved.' })
      closeTarget()
      setTargetForm({ branch_id: '', period_type: 'DAILY', quantity: 10, effective_from: '', effective_to: '' })
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const errorBanner = error ? (
    <Alert color="red" icon={<IconAlertCircle size={16} />}>
      {error}
    </Alert>
  ) : null

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }}>
      <Card shadow="sm" radius="md" withBorder>
        <Group justify="space-between" mb="sm">
          <Title order={5}>Commission rules</Title>
          <Button size="xs" onClick={openRule}>
            New rule
          </Button>
        </Group>
        {rules.isLoading ? (
          <Loader />
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Name</Table.Th>
                <Table.Th ta="right">/ SIM</Table.Th>
                <Table.Th>Effective</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(rules.data ?? []).map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>{r.name}</Table.Td>
                  <Table.Td ta="right">{r.amount_per_sim}</Table.Td>
                  <Table.Td>
                    {new Date(r.effective_from).toLocaleDateString()}
                    {r.effective_to ? ` → ${new Date(r.effective_to).toLocaleDateString()}` : ''}
                  </Table.Td>
                </Table.Tr>
              ))}
              {(rules.data ?? []).length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={3}>
                    <Text size="sm" c="dimmed" ta="center">
                      No commission rules yet.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Card shadow="sm" radius="md" withBorder>
        <Group justify="space-between" mb="sm">
          <Title order={5}>Branch targets</Title>
          <Button size="xs" onClick={openTarget}>
            New target
          </Button>
        </Group>
        {targets.isLoading ? (
          <Loader />
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Branch</Table.Th>
                <Table.Th>Period</Table.Th>
                <Table.Th ta="right">Qty</Table.Th>
                <Table.Th>Effective</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(targets.data ?? []).map((t) => (
                <Table.Tr key={t.id}>
                  <Table.Td>{branches.data?.find((b) => b.id === t.branch_id)?.name ?? t.branch_id}</Table.Td>
                  <Table.Td>
                    <Badge variant="light">{t.period_type}</Badge>
                  </Table.Td>
                  <Table.Td ta="right">{t.quantity}</Table.Td>
                  <Table.Td>
                    {new Date(t.effective_from).toLocaleDateString()}
                    {t.effective_to ? ` → ${new Date(t.effective_to).toLocaleDateString()}` : ''}
                  </Table.Td>
                </Table.Tr>
              ))}
              {(targets.data ?? []).length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={4}>
                    <Text size="sm" c="dimmed" ta="center">
                      No branch targets yet.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Modal opened={ruleOpen} onClose={closeRule} title="New commission rule">
        <form onSubmit={submitRule}>
          <Stack gap="sm">
            <TextInput
              label="Name"
              value={ruleForm.name}
              onChange={(e) => setRuleForm({ ...ruleForm, name: e.currentTarget.value })}
              required
            />
            <TextInput
              label="Amount per SIM"
              value={ruleForm.amount_per_sim}
              onChange={(e) => setRuleForm({ ...ruleForm, amount_per_sim: e.currentTarget.value })}
              required
            />
            <TextInput
              label="Effective from"
              type="datetime-local"
              value={ruleForm.effective_from}
              onChange={(e) => setRuleForm({ ...ruleForm, effective_from: e.currentTarget.value })}
              required
            />
            <TextInput
              label="Effective to (optional)"
              type="datetime-local"
              value={ruleForm.effective_to}
              onChange={(e) => setRuleForm({ ...ruleForm, effective_to: e.currentTarget.value })}
            />
            {errorBanner}
            <Group justify="flex-end">
              <Button type="submit">Create rule</Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      <Modal opened={targetOpen} onClose={closeTarget} title="New branch target">
        <form onSubmit={submitTarget}>
          <Stack gap="sm">
            <Select
              label="Branch"
              searchable
              data={(branches.data ?? []).map((b) => ({ value: String(b.id), label: b.name }))}
              value={targetForm.branch_id}
              onChange={(v) => setTargetForm({ ...targetForm, branch_id: v ?? '' })}
              required
            />
            <Select
              label="Period"
              data={['DAILY', 'WEEKLY', 'MONTHLY']}
              value={targetForm.period_type}
              onChange={(v) => setTargetForm({ ...targetForm, period_type: v ?? 'DAILY' })}
            />
            <NumberInput
              label="Quantity"
              min={1}
              value={targetForm.quantity}
              onChange={(v) => setTargetForm({ ...targetForm, quantity: typeof v === 'number' ? v : 1 })}
              required
            />
            <TextInput
              label="Effective from"
              type="datetime-local"
              value={targetForm.effective_from}
              onChange={(e) => setTargetForm({ ...targetForm, effective_from: e.currentTarget.value })}
              required
            />
            <TextInput
              label="Effective to (optional)"
              type="datetime-local"
              value={targetForm.effective_to}
              onChange={(e) => setTargetForm({ ...targetForm, effective_to: e.currentTarget.value })}
            />
            {errorBanner}
            <Group justify="flex-end">
              <Button type="submit">Create target</Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </SimpleGrid>
  )
}

function FlagsAndNotifications() {
  const flags = useFlags()
  const notificationsList = useNotifications()
  const flagActions = useFlagActions()
  const markRead = useMarkNotificationRead()

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }}>
      <Card shadow="sm" radius="md" withBorder>
        <Title order={5} mb="sm">
          Inactivity flags
        </Title>
        {flags.isLoading ? (
          <Loader />
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>User</Table.Th>
                <Table.Th>Role</Table.Th>
                <Table.Th>Flagged</Table.Th>
                <Table.Th>Last login</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(flags.data ?? []).map((f) => (
                <Table.Tr key={f.id}>
                  <Table.Td>#{f.user_id}</Table.Td>
                  <Table.Td>{f.role}</Table.Td>
                  <Table.Td>{new Date(f.flagged_at).toLocaleString()}</Table.Td>
                  <Table.Td>{f.last_login_at ? new Date(f.last_login_at).toLocaleString() : '—'}</Table.Td>
                  <Table.Td>
                    <Badge color={f.resolved_at ? 'teal' : 'red'} variant="light">
                      {f.resolved_at ? 'Resolved' : 'Active'}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {!f.resolved_at && (
                      <Button
                        size="xs"
                        variant="outline"
                        onClick={() => flagActions.mutateAsync({ id: f.id, action: 'acknowledge' })}
                      >
                        Acknowledge
                      </Button>
                    )}
                  </Table.Td>
                </Table.Tr>
              ))}
              {(flags.data ?? []).length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={6}>
                    <Text size="sm" c="dimmed" ta="center">
                      No inactive-account flags.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        )}
      </Card>

      <Card shadow="sm" radius="md" withBorder>
        <Title order={5} mb="sm">
          Notifications feed
        </Title>
        {notificationsList.isLoading ? (
          <Loader />
        ) : (
          <Table>
            <Table.Tbody>
              {(notificationsList.data ?? []).map((n) => (
                <Table.Tr key={n.id}>
                  <Table.Td px="sm" py="xs">
                    <Group justify="space-between" wrap="nowrap">
                      <Stack gap={2}>
                        <Text size="sm" fw={n.is_read ? 400 : 600}>
                          {n.title}
                        </Text>
                        {n.body && (
                          <Text size="xs" c="dimmed">
                            {n.body}
                          </Text>
                        )}
                        <Text size="xs" c="dimmed">
                          {new Date(n.created_at).toLocaleString()}
                        </Text>
                      </Stack>
                      {!n.is_read && (
                        <Button
                          size="xs"
                          variant="subtle"
                          onClick={() => markRead.mutateAsync(n.id)}
                        >
                          Mark read
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
              {(notificationsList.data ?? []).length === 0 && (
                <Table.Tr>
                  <Table.Td>
                    <Text size="sm" c="dimmed" ta="center">
                      No notifications.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </SimpleGrid>
  )
}

export default function Management() {
  const [tab, setTab] = useState<'accounts' | 'commission' | 'flags'>('accounts')
  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Management</Title>
        <Button.Group>
          <Button
            variant={tab === 'accounts' ? 'filled' : 'default'}
            onClick={() => setTab('accounts')}
          >
            Accounts
          </Button>
          <Button
            variant={tab === 'commission' ? 'filled' : 'default'}
            onClick={() => setTab('commission')}
          >
            Commission
          </Button>
          <Button
            variant={tab === 'flags' ? 'filled' : 'default'}
            onClick={() => setTab('flags')}
          >
            Flags &amp; alerts
          </Button>
        </Button.Group>
      </Group>

      {tab === 'accounts' && (
        <Stack gap="md">
          <Branches />
          <Ambassadors />
        </Stack>
      )}
      {tab === 'commission' && <Commission />}
      {tab === 'flags' && <FlagsAndNotifications />}
    </Stack>
  )
}