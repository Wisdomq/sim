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
  Progress,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { notifications } from '@mantine/notifications'
import { IconAlertCircle, IconUpload } from '@tabler/icons-react'
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { errorMessage } from '../lib/api'
import {
  createReturnRequest,
  distributeStock,
  simStatusLabels,
  type SimStatus,
  uploadPickList,
  useBoxScanIntake,
  useBranches,
  useReturnRequests,
  useSimCards,
} from '../lib/stock'

type Tab = 'intake' | 'distribute' | 'returns'

const statusOptions: { value: SimStatus; label: string }[] = Object.entries(simStatusLabels).map(
  ([value, label]) => ({ value: value as SimStatus, label }),
)

function toSerials(value: string): string[] {
  return value
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function IntakeForm() {
  const { mutateAsync: boxScan, isPending: scanning } = useBoxScanIntake()

  const [file, setFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [lastResult, setLastResult] = useState<string | null>(null)

  const [boxBarcode, setBoxBarcode] = useState('')
  const [firstSerial, setFirstSerial] = useState('')
  const [quantity, setQuantity] = useState<number>(100)
  const [expiry, setExpiry] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function onPickList() {
    if (!file) return
    setUploading(true)
    setError(null)
    setProgress(0)
    try {
      const { task_id: taskId } = await uploadPickList(file, setProgress)
      setParsing(true)
      setLastResult(`Pick list submitted (task ${taskId.slice(0, 8)}). Parsing in the background.`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setUploading(false)
    }
  }

  async function onBoxScan(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const result = await boxScan({
        box_barcode: boxBarcode.trim(),
        first_serial: firstSerial.trim() || undefined,
        quantity: firstSerial.trim() ? quantity : undefined,
        expiry_date: expiry || undefined,
      })
      setLastResult(
        `Intake complete: ${result.inserted_count} inserted, ${result.duplicate_count} duplicates (${result.source_reference}).`,
      )
      setBoxBarcode('')
      setFirstSerial('')
      setQuantity(100)
      setExpiry('')
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }}>
      <Card shadow="sm" radius="md" withBorder>
        <Title order={5} mb="sm">
          Pick-list PDF
        </Title>
        <Stack gap="sm">
          <FileInput
            label="Pick-list PDF"
            placeholder="Choose a Safaricom pick-list PDF"
            accept="application/pdf"
            value={file}
            onChange={setFile}
            clearable
          />
          {uploading && (
            <div>
              <Progress value={progress} size="sm" />
              <Text size="xs" c="dimmed" mt={4}>
                Uploading… {progress}%
              </Text>
            </div>
          )}
          {parsing && (
            <Group gap="xs">
              <Loader size="xs" />
              <Text size="sm" c="dimmed">
                Parsing queued — new SIMs will appear in stock below.
              </Text>
            </Group>
          )}
          <Button
            leftSection={<IconUpload size={16} />}
            loading={uploading}
            disabled={!file}
            onClick={onPickList}
          >
            Upload pick list
          </Button>
        </Stack>
      </Card>

      <Card shadow="sm" radius="md" withBorder>
        <Title order={5} mb="sm">
          Box-scan intake
        </Title>
        <form onSubmit={onBoxScan}>
          <Stack gap="sm">
            <TextInput
              label="Box barcode"
              placeholder="e.g. 890127..."
              value={boxBarcode}
              onChange={(e) => setBoxBarcode(e.currentTarget.value)}
              required
            />
            <SimpleGrid cols={{ base: 2 }}>
              <TextInput
                label="First serial"
                placeholder="e.g. 89410X..."
                value={firstSerial}
                onChange={(e) => setFirstSerial(e.currentTarget.value)}
              />
              <NumberInput
                label="Quantity"
                min={1}
                max={100}
                value={quantity}
                onChange={(v) => setQuantity(typeof v === 'number' ? v : 100)}
              />
            </SimpleGrid>
            <TextInput
              label="Expiry date (optional)"
              placeholder="YYYY-MM-DD"
              value={expiry}
              onChange={(e) => setExpiry(e.currentTarget.value)}
            />
            {error && (
              <Alert color="red" icon={<IconAlertCircle size={16} />}>
                {error}
              </Alert>
            )}
            <Group justify="flex-end">
              <Button type="submit" loading={scanning}>
                Scan box into stock
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
      {lastResult && (
        <Alert color="green" onClose={() => setLastResult(null)} withCloseButton>
          {lastResult}
        </Alert>
      )}
    </SimpleGrid>
  )
}

function DistributeForm() {
  const branches = useBranches()
  const qc = useQueryClient()
  const [branchId, setBranchId] = useState<string | null>(null)
  const [quantity, setQuantity] = useState<number | ''>(10)
  const [serials, setSerials] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!branchId) return
    setBusy(true)
    setError(null)
    try {
      const list = toSerials(serials)
      await distributeStock({
        branch_id: Number(branchId),
        ...(list.length > 0 ? { serial_numbers: list } : { quantity: Number(quantity) }),
      })
      notifications.show({ title: 'Stock distributed', message: 'SIMs moved to the branch.' })
      setSerials('')
      await qc.invalidateQueries({ queryKey: ['sim-cards'] })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card shadow="sm" radius="md" withBorder maw={560}>
      <Title order={5} mb="sm">
        Distribute stock to a branch
      </Title>
      <form onSubmit={onSubmit}>
        <Stack gap="sm">
          <Select
            label="Branch"
            placeholder="Select a branch"
            data={(branches.data ?? []).map((b) => ({ value: String(b.id), label: b.name }))}
            value={branchId}
            onChange={setBranchId}
            searchable
            required
          />
          <NumberInput
            label="Quantity (when using first-serial ranges)"
            min={1}
            value={quantity}
            onChange={(v) => setQuantity(typeof v === 'number' ? v : '')}
          />
          <Textarea
            label="Or explicit serial numbers"
            placeholder="List serials, space or comma separated"
            value={serials}
            onChange={(e) => setSerials(e.currentTarget.value)}
            autosize
            minRows={2}
          />
          {error && (
            <Alert color="red" icon={<IconAlertCircle size={16} />}>
              {error}
            </Alert>
          )}
          <Group justify="flex-end">
            <Button type="submit" loading={busy} disabled={!branchId}>
              Distribute
            </Button>
          </Group>
        </Stack>
      </form>
    </Card>
  )
}

function StockTable() {
  const [status, setStatus] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const pageSize = 50
  const sims = useSimCards(status ? { status: status as SimStatus } : undefined)

  const paginatedSims = (sims.data ?? []).slice((page - 1) * pageSize, page * pageSize)
  const totalPages = Math.ceil((sims.data?.length ?? 0) / pageSize)

  const getExpiryStatus = (expiryDate: string | null) => {
    if (!expiryDate) return null
    const expiry = new Date(expiryDate)
    const today = new Date()
    const daysUntilExpiry = Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    
    if (daysUntilExpiry < 0) return { color: 'red', label: 'Expired' }
    if (daysUntilExpiry <= 7) return { color: 'orange', label: `${daysUntilExpiry}d left` }
    if (daysUntilExpiry <= 30) return { color: 'yellow', label: `${daysUntilExpiry}d left` }
    return null
  }

  const getStatusColor = (status: SimStatus) => {
    switch (status) {
      case 'IN_HQ_STOCK': return 'blue'
      case 'WITH_BRANCH': return 'cyan'
      case 'WITH_BA': return 'purple'
      case 'SOLD': return 'green'
      case 'RETURNED_TO_BRANCH': return 'orange'
      case 'RETURNED_TO_HQ': return 'grape'
      case 'EXPIRED': return 'red'
      default: return 'gray'
    }
  }

  return (
    <Card shadow="sm" radius="md" withBorder>
      <Group justify="space-between" mb="sm">
        <Title order={5}>Current stock ({sims.data?.length ?? 0} total)</Title>
        <Select
          placeholder="All statuses"
          clearable
          data={statusOptions}
          value={status}
          onChange={setStatus}
          w={220}
        />
      </Group>
      {sims.isLoading ? (
        <Loader />
      ) : (
        <>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Serial number</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Branch</Table.Th>
                <Table.Th>Expiry</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {sims.data?.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={4}>
                    <Text size="sm" c="dimmed" ta="center">
                      No SIMs yet — add stock via intake.
                    </Text>
                  </Table.Td>
                </Table.Tr>
              )}
              {paginatedSims.map((sim) => {
                const expiryStatus = getExpiryStatus(sim.expiry_date)
                return (
                  <Table.Tr key={sim.id}>
                    <Table.Td>{sim.serial_number}</Table.Td>
                    <Table.Td>
                      <Badge color={getStatusColor(sim.status)} variant="light">
                        {simStatusLabels[sim.status]}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{sim.current_branch_id ?? '—'}</Table.Td>
                    <Table.Td>
                      <Group gap={4}>
                        <Text size="sm">{sim.expiry_date ?? '—'}</Text>
                        {expiryStatus && (
                          <Badge size="xs" color={expiryStatus.color} variant="filled">
                            {expiryStatus.label}
                          </Badge>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                )
              })}
            </Table.Tbody>
          </Table>
          {totalPages > 1 && (
            <Group justify="center" mt="md">
              <Button
                size="xs"
                variant="light"
                disabled={page === 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Text size="sm">
                Page {page} of {totalPages}
              </Text>
              <Button
                size="xs"
                variant="light"
                disabled={page === totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              >
                Next
              </Button>
            </Group>
          )}
        </>
      )}
    </Card>
  )
}

function Returns() {
  const requests = useReturnRequests()
  const branches = useBranches()
  const [opened, { open, close }] = useDisclosure()
  const [branchId, setBranchId] = useState<string | null>(null)
  const [serials, setSerials] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!branchId) return
    setBusy(true)
    setError(null)
    try {
      await createReturnRequest({
        branch_id: Number(branchId),
        serial_numbers: toSerials(serials),
        reason: reason || undefined,
      })
      notifications.show({
        title: 'Return request created',
        message: 'The branch will fulfill it from the mobile app.',
      })
      close()
      setBranchId(null)
      setSerials('')
      setReason('')
      await requests.refetch()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card shadow="sm" radius="md" withBorder>
      <Group justify="space-between" mb="sm">
        <Title order={5}>Stock return requests</Title>
        <Button onClick={open}>New return request</Button>
      </Group>
      {requests.isLoading ? (
        <Loader />
      ) : (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Serial</Table.Th>
              <Table.Th>Branch</Table.Th>
              <Table.Th>Reason</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Requested</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {requests.data?.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={5}>
                  <Text size="sm" c="dimmed" ta="center">
                    No return requests.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
            {(requests.data ?? []).map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>{r.serial_number ?? `SIM #${r.sim_card_id}`}</Table.Td>
                <Table.Td>{branches.data?.find((b) => b.id === r.branch_id)?.name ?? r.branch_id}</Table.Td>
                <Table.Td>{r.reason ?? '—'}</Table.Td>
                <Table.Td>
                  <Badge color={r.status === 'COMPLETED' ? 'teal' : 'yellow'} variant="light">
                    {r.status}
                  </Badge>
                </Table.Td>
                <Table.Td>{new Date(r.return_date).toLocaleString()}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={opened} onClose={close} title="New stock return request">
        <form onSubmit={onSubmit}>
          <Stack gap="sm">
            <Select
              label="Branch"
              placeholder="Select branch"
              data={(branches.data ?? []).map((b) => ({ value: String(b.id), label: b.name }))}
              value={branchId}
              onChange={setBranchId}
              searchable
              required
            />
            <Textarea
              label="Serial numbers"
              placeholder="Space or comma separated"
              value={serials}
              onChange={(e) => setSerials(e.currentTarget.value)}
              required
              minRows={2}
            />
            <TextInput
              label="Reason (optional)"
              value={reason}
              onChange={(e) => setReason(e.currentTarget.value)}
              placeholder="e.g. damaged stock"
            />
            {error && (
              <Alert color="red" icon={<IconAlertCircle size={16} />}>
                {error}
              </Alert>
            )}
            <Group justify="flex-end">
              <Button type="submit" loading={busy}>
                Create request
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Card>
  )
}

export default function Stock() {
  const [tab, setTab] = useState<Tab>('intake')
  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Stock</Title>
        <SegmentedControl
          value={tab}
          onChange={(v) => setTab(v as Tab)}
          data={[
            { label: 'Intake', value: 'intake' },
            { label: 'Distribute', value: 'distribute' },
            { label: 'Returns', value: 'returns' },
          ]}
        />
      </Group>
      {tab === 'intake' && (
        <>
          <IntakeForm />
          <StockTable />
        </>
      )}
      {tab === 'distribute' && (
        <>
          <DistributeForm />
          <StockTable />
        </>
      )}
      {tab === 'returns' && <Returns />}
    </Stack>
  )
}