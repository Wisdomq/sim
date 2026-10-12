import {
  Alert,
  Badge,
  Button,
  Card,
  FileInput,
  Group,
  Loader,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { useQueryClient } from '@tanstack/react-query'
import { notifications } from '@mantine/notifications'
import { IconAlertCircle, IconUpload } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useState } from 'react'
import { errorMessage } from '../lib/api'
import {
  matchStatusLabels,
  pollImport,
  uploadReconReport,
  useActivatedByMonth,
  useImportDetail,
  useImportResult,
  useImports,
  type MatchStatus,
  type SafaricomImport,
} from '../lib/recon'
import { formatMoney } from '../lib/reports'

function UploadCard({ onQueued }: { onQueued: (importId: number) => void }) {
  const qc = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [reportDate, setReportDate] = useState<string>(() => dayjs().subtract(1, 'day').format('YYYY-MM-DD'))
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [polling, setPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !reportDate) return
    setUploading(true)
    setError(null)
    setProgress(0)
    try {
      const { import_id: importId } = await uploadReconReport(
        file,
        reportDate,
        setProgress,
      )
      setUploading(false)
      setPolling(true)
      notifications.show({ title: 'Upload queued', message: `Import #${importId} is being reconciled.` })
      onQueued(importId)
      await pollImport(importId, qc, () => {
        setPolling(false)
        notifications.show({
          title: 'Reconciliation complete',
          message: `Import #${importId} finished.`,
        })
      })
      setFile(null)
    } catch (err) {
      setError(errorMessage(err))
      setUploading(false)
      setPolling(false)
    }
  }

  return (
    <Card shadow="sm" radius="md" withBorder>
      <Title order={5} mb="sm">
        Upload Safaricom line report
      </Title>
      <form onSubmit={onSubmit}>
        <Stack gap="sm">
          <FileInput
            label="Report file (.xlsx)"
            placeholder="Safaricom xlsx line-connection report"
            accept=".xlsx"
            value={file}
            onChange={setFile}
            clearable
            required
          />
          <TextInput
            label="Report date"
            type="date"
            value={reportDate}
            onChange={(e) => setReportDate(e.currentTarget.value)}
            required
          />
          {uploading && (
            <div>
              <Progress value={progress} size="sm" />
              <Text size="xs" c="dimmed" mt={4}>
                Uploading… {progress}%
              </Text>
            </div>
          )}
          {polling && (
            <Group gap="xs">
              <Loader size="xs" />
              <Text size="sm" c="dimmed">
                Reconciling in the background — you can keep working.
              </Text>
            </Group>
          )}
          {error && (
            <Alert color="red" icon={<IconAlertCircle size={16} />}>
              {error}
            </Alert>
          )}
          <Group justify="flex-end">
            <Button
              type="submit"
              loading={uploading || polling}
              disabled={!file || !reportDate}
              leftSection={!uploading && !polling ? <IconUpload size={16} /> : undefined}
            >
              {polling ? 'Reconciling…' : 'Upload & reconcile'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Card>
  )
}

function ImportRows({ imports, active, onSelect }: { imports: SafaricomImport[]; active: number | null; onSelect: (id: number) => void }) {
  return (
    <Table striped highlightOnHover>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>#</Table.Th>
          <Table.Th>Report date</Table.Th>
          <Table.Th>Uploaded</Table.Th>
          <Table.Th ta="right">Rows</Table.Th>
          <Table.Th>Status</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {(imports ?? []).map((imp) => (
          <Table.Tr
            key={imp.id}
            onClick={() => onSelect(imp.id)}
            style={{ cursor: 'pointer' }}
            bg={active === imp.id ? 'var(--mantine-color-blue-0)' : undefined}
          >
            <Table.Td>{imp.id}</Table.Td>
            <Table.Td>{imp.report_date}</Table.Td>
            <Table.Td>{dayjs(imp.uploaded_at).format('D MMM YYYY, HH:mm')}</Table.Td>
            <Table.Td ta="right">{imp.row_count}</Table.Td>
            <Table.Td>
              <Badge color={imp.status === 'COMPLETED' ? 'teal' : imp.status === 'FAILED' ? 'red' : 'yellow'} variant="light">
                {imp.status}
              </Badge>
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  )
}

function DetailPanel({ importId }: { importId: number }) {
  const [status, setStatus] = useState<string | null>(null)
  const result = useImportResult(importId)
  const detail = useImportDetail(importId, (status ?? null) as MatchStatus | null)

  if (result.isError) {
    return (
      <Alert color="blue">
        This import has not finished reconciling yet — results will appear shortly.
      </Alert>
    )
  }
  const r = result.data
  if (!r) return <Loader />

  return (
    <Stack gap="md">
      <SimpleGrid cols={{ base: 2, md: 5 }}>
        <Card shadow="sm" radius="md" withBorder>
          <Text size="sm" c="dimmed">Sold in app</Text>
          <Text size="xl" fw={700}>{r.total_sold_in_app}</Text>
        </Card>
        <Card shadow="sm" radius="md" withBorder>
          <Text size="sm" c="dimmed">Activated by Safaricom</Text>
          <Text size="xl" fw={700}>{r.total_confirmed_activated_by_safaricom}</Text>
        </Card>
        <Card shadow="sm" radius="md" withBorder>
          <Text size="sm" c="dimmed">Cumulative commission</Text>
          <Text size="xl" fw={700}>{formatMoney(r.total_cumulative_commission)}</Text>
        </Card>
        <Card shadow="sm" radius="md" withBorder>
          <Text size="sm" c="dimmed">Top-ups</Text>
          <Text size="xl" fw={700}>{r.total_topped_up}</Text>
        </Card>
        <Card shadow="sm" radius="md" withBorder>
          <Text size="sm" c="dimmed">Fraud flagged</Text>
          <Text size="xl" fw={700} c={r.total_fraud_flagged > 0 ? 'red' : undefined}>
            {r.total_fraud_flagged}
          </Text>
        </Card>
      </SimpleGrid>

      <SimpleGrid cols={{ base: 2, md: 3 }}>
        <Card shadow="sm" radius="md" withBorder>
          <Text size="sm" c="dimmed">Sold, not in Safaricom</Text>
          <Text size="lg" fw={700}>{r.unmatched_sold_not_in_safaricom_count}</Text>
        </Card>
        <Card shadow="sm" radius="md" withBorder>
          <Text size="sm" c="dimmed">In Safaricom, not sold</Text>
          <Text size="lg" fw={700}>{r.unmatched_in_safaricom_not_sold_in_app_count}</Text>
        </Card>
      </SimpleGrid>

      <Card shadow="sm" radius="md" withBorder>
        <Group justify="space-between" mb="sm">
          <Title order={5}>Line detail</Title>
          <Select
            placeholder="All match statuses"
            clearable
            data={Object.entries(matchStatusLabels).map(([value, label]) => ({ value, label }))}
            value={status}
            onChange={setStatus}
            w={240}
          />
        </Group>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Serial</Table.Th>
              <Table.Th>Match status</Table.Th>
              <Table.Th>Top-up</Table.Th>
              <Table.Th>Amount</Table.Th>
              <Table.Th>Commission</Table.Th>
              <Table.Th>Fraud</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(detail.data ?? []).map((line) => (
              <Table.Tr key={line.id}>
                <Table.Td>{line.serial_number ?? '—'}</Table.Td>
                <Table.Td>
                  <Badge color={line.match_status === 'MATCHED' ? 'teal' : line.match_status === 'SOLD_NOT_ACTIVATED' ? 'orange' : 'violet'} variant="light">
                    {matchStatusLabels[line.match_status]}
                  </Badge>
                </Table.Td>
                <Table.Td>{line.top_up_date ?? '—'}</Table.Td>
                <Table.Td>{line.top_up_amount ? formatMoney(line.top_up_amount) : '—'}</Table.Td>
                <Table.Td>{line.cumulative_commission ? formatMoney(line.cumulative_commission) : '—'}</Table.Td>
                <Table.Td>
                  {line.fraud_flagged ? (
                    <Badge color="red">{line.fraud_reason ?? 'Fraud'}</Badge>
                  ) : (
                    '—'
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
            {(detail.data ?? []).length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text size="sm" c="dimmed" ta="center">
                    No lines for this filter.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Stack>
  )
}

function ActivatedByMonth() {
  const [month, setMonth] = useState<string>(() => dayjs().format('YYYY-MM'))
  const activated = useActivatedByMonth(month)
  return (
    <Card shadow="sm" radius="md" withBorder>
      <Group justify="space-between" mb="sm">
        <Title order={5}>Activated serials by month</Title>
        <TextInput
          type="month"
          value={month}
          onChange={(e) => setMonth(e.currentTarget.value)}
          w={160}
        />
      </Group>
      <Text size="xs" c="dimmed" mb="xs">
        Showing up to the first 200 serials activated in this month.
      </Text>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Serial</Table.Th>
            <Table.Th>Top-up date</Table.Th>
            <Table.Th>Top-up amount</Table.Th>
            <Table.Th>Cumulative commission</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(activated.data ?? []).map((line) => (
            <Table.Tr key={line.id}>
              <Table.Td>{line.serial_number ?? '—'}</Table.Td>
              <Table.Td>{line.top_up_date ?? '—'}</Table.Td>
              <Table.Td>{line.top_up_amount ? formatMoney(line.top_up_amount) : '—'}</Table.Td>
              <Table.Td>{line.cumulative_commission ? formatMoney(line.cumulative_commission) : '—'}</Table.Td>
            </Table.Tr>
          ))}
          {(activated.data ?? []).length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={4}>
                <Text size="sm" c="dimmed" ta="center">
                  No activated serials for this month.
                </Text>
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>
    </Card>
  )
}

export default function Reconciliation() {
  const imports = useImports()
  const [activeId, setActiveId] = useState<number | null>(null)

  return (
    <Stack gap="md">
      <Title order={3}>Reconciliation</Title>
      <SimpleGrid cols={{ base: 1, lg: 2 }}>
        <UploadCard onQueued={(id) => setActiveId(id)} />
        <Card shadow="sm" radius="md" withBorder>
          <Title order={5} mb="sm">
            Imports
          </Title>
          {imports.isLoading ? (
            <Loader />
          ) : (
            <ImportRows
              imports={imports.data ?? []}
              active={activeId}
              onSelect={setActiveId}
            />
          )}
        </Card>
      </SimpleGrid>

      {activeId !== null && <DetailPanel key={activeId} importId={activeId} />}
      <ActivatedByMonth />
    </Stack>
  )
}