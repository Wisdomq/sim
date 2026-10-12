import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  UnstyledButton,
} from '@mantine/core'
import { IconAlertCircle, IconChevronDown, IconChevronUp, IconUpload, IconSettings, IconTruck, IconReport, IconChartBar } from '@tabler/icons-react'
import { useState } from 'react'
import dayjs from 'dayjs'
import {
  dispatchExport,
  formatDate,
  formatMoney,
  formatPercent,
  periodDefaults,
  useReport,
  useReportFiles,
  downloadReportFile,
  type PeriodType,
} from '../lib/reports'
import { errorMessage } from '../lib/api'
import { notifications } from '@mantine/notifications'
import { useFlags } from '../lib/hq'
import { Link } from 'react-router-dom'

const statusLabels: [keyof import('../types/api').StockCountsByStatus, string][] = [
  ['in_hq_stock', 'In HQ stock'],
  ['with_branch', 'With branch'],
  ['with_ba', 'With BA'],
  ['sold', 'Sold'],
  ['returned_to_branch', 'Returned to branch'],
  ['returned_to_hq', 'Returned to HQ'],
  ['expired', 'Expired'],
]

export default function Dashboard() {
  const [period, setPeriod] = useState<PeriodType>('WEEKLY')
  const defaults = periodDefaults(period)
  const [range, setRange] = useState<[string, string]>([defaults.start, defaults.end])
  const [openBranches, setOpenBranches] = useState<Set<number>>(new Set())
  const {
    data: report,
    isFetching,
    isError,
    error,
  } = useReport(period, range)
  const files = useReportFiles()
  const openFlags = useFlags({ resolved: false })

  const [exporting, setExporting] = useState<'PDF' | 'XLSX' | null>(null)

  function changePeriod(next: PeriodType) {
    setPeriod(next)
    const d = periodDefaults(next)
    setRange([d.start, d.end])
  }

  async function onExport(format: 'PDF' | 'XLSX') {
    setExporting(format)
    try {
      await dispatchExport(period, range[0], range[1], format)
      notifications.show({
        title: `Export queued`,
        message: `${format} report for ${formatDate(range[0])}–${formatDate(range[1])} is being generated.`,
      })
      window.setTimeout(() => files.refetch(), 800)
    } catch (err) {
      notifications.show({
        color: 'red',
        title: 'Export failed',
        message: errorMessage(err),
      })
    } finally {
      setExporting(null)
    }
  }

  const toggleBranch = (id: number) => {
    setOpenBranches((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const hasData = report && report.branch_reports.length > 0

  return (
    <Stack gap="md">
      <Group justify="space-between" wrap="wrap">
        <Title order={3}>Dashboard</Title>
        <SegmentedControl
          value={period}
          onChange={(v) => changePeriod(v as PeriodType)}
          data={['DAILY', 'WEEKLY', 'MONTHLY']}
        />
      </Group>

      <Group gap="md" wrap="wrap" align="center">
        <Group gap="xs" align="center">
          <TextInput
            w={150}
            type="date"
            aria-label="Report start date"
            value={range[0]}
            onChange={(e) => setRange([e.currentTarget.value, range[1]])}
          />
          <Text c="dimmed">→</Text>
          <TextInput
            w={150}
            type="date"
            aria-label="Report end date"
            value={range[1]}
            onChange={(e) => setRange([range[0], e.currentTarget.value])}
          />
        </Group>
        {isFetching && <Loader size="sm" />}
        <Group gap="xs">
          <Button size="xs" color="red" variant="light" loading={exporting === 'PDF'} onClick={() => onExport('PDF')}>
            Export PDF
          </Button>
          <Button size="xs" color="green" variant="light" loading={exporting === 'XLSX'} onClick={() => onExport('XLSX')}>
            Export Excel
          </Button>
        </Group>
      </Group>

      {/* Quick Actions */}
      <SimpleGrid cols={{ base: 2, md: 4 }}>
        <Button
          variant="light"
          size="sm"
          leftSection={<IconUpload size={16} />}
          component={Link}
          to="/reconciliation"
        >
          Upload Report
        </Button>
        <Button
          variant="light"
          size="sm"
          leftSection={<IconTruck size={16} />}
          component={Link}
          to="/stock"
        >
          Distribute Stock
        </Button>
        <Button
          variant="light"
          size="sm"
          leftSection={<IconSettings size={16} />}
          component={Link}
          to="/management"
        >
          Manage Accounts
        </Button>
        <Button
          variant="light"
          size="sm"
          leftSection={<IconReport size={16} />}
          component={Link}
          to="/management"
        >
          View Flags
        </Button>
      </SimpleGrid>

      {isError && (
        <Alert color="red" icon={<IconAlertCircle size={16} />}>
          {errorMessage(error)}
        </Alert>
      )}

      {openFlags.data && openFlags.data.length > 0 && (
        <Alert color="red" icon={<IconAlertCircle size={16} />} title="Critical: Inactivity Flags">
          <Group justify="space-between" wrap="wrap">
            <Text fw={500}>
              {openFlags.data.length} account{openFlags.data.length > 1 ? 's' : ''} flagged inactive
              (no login for 3+ days).
            </Text>
            <Button size="xs" variant="filled" color="red" component={Link} to="/management">
              Resolve Now
            </Button>
          </Group>
        </Alert>
      )}

      {!report && isFetching && <Loader />}

      {report && !hasData && (
        <Alert color="blue">No branch data for this period yet.</Alert>
      )}

      {report && hasData && (
        <>
          <SimpleGrid cols={{ base: 1, md: 4 }}>
            <Card shadow="sm" radius="md" withBorder>
              <Text size="sm" c="dimmed">
                Total stock
              </Text>
              <Text size="xl" fw={700}>
                {report.total_stock_counts.sold +
                  report.total_stock_counts.with_ba +
                  report.total_stock_counts.with_branch +
                  report.total_stock_counts.in_hq_stock +
                  report.total_stock_counts.returned_to_branch +
                  report.total_stock_counts.returned_to_hq +
                  report.total_stock_counts.expired}{' '}
                <Text span c="dimmed" size="sm">
                  SIMs
                </Text>
              </Text>
            </Card>
            <Card shadow="sm" radius="md" withBorder>
              <Text size="sm" c="dimmed">
                Sales
              </Text>
              <Text size="xl" fw={700}>
                {report.total_sales_count} <Text span c="dimmed" size="sm">SIMs</Text>
              </Text>
            </Card>
            <Card shadow="sm" radius="md" withBorder>
              <Text size="sm" c="dimmed">
                Commission owed
              </Text>
              <Text size="xl" fw={700}>
                {formatMoney(report.total_commission_owed)}
              </Text>
            </Card>
            <Card shadow="sm" radius="md" withBorder>
              <Text size="sm" c="dimmed">
                Overall performance
              </Text>
              <Text size="xl" fw={700}>
                {formatPercent(report.overall_performance_percentage)}
              </Text>
            </Card>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, lg: 2 }}>
            <Card shadow="sm" radius="md" withBorder>
              <Title order={5} mb="sm">
                Stock by status
              </Title>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Status</Table.Th>
                    <Table.Th ta="right">Count</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {statusLabels.map(([key, label]) => (
                    <Table.Tr key={key}>
                      <Table.Td>{label}</Table.Td>
                      <Table.Td ta="right">{report.total_stock_counts[key]}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Card>

            <Card shadow="sm" radius="md" withBorder>
              <Title order={5} mb="sm">
                Reconciliation headlines
              </Title>
              {report.reconciliation_headlines ? (
                <Table>
                  <Table.Tbody>
                    <Table.Tr>
                      <Table.Td>Confirmed activated by Safaricom</Table.Td>
                      <Table.Td ta="right">{report.reconciliation_headlines.total_confirmed_activated_by_safaricom}</Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td>Cumulative commission</Table.Td>
                      <Table.Td ta="right">{formatMoney(report.reconciliation_headlines.total_cumulative_commission)}</Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td>Fraud flagged</Table.Td>
                      <Table.Td ta="right">{report.reconciliation_headlines.total_fraud_flagged}</Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td>Sold, not in Safaricom</Table.Td>
                      <Table.Td ta="right">{report.reconciliation_headlines.unmatched_sold_not_in_safaricom_count}</Table.Td>
                    </Table.Tr>
                    <Table.Tr>
                      <Table.Td>In Safaricom, not sold in app</Table.Td>
                      <Table.Td ta="right">{report.reconciliation_headlines.unmatched_in_safaricom_not_sold_in_app_count}</Table.Td>
                    </Table.Tr>
                  </Table.Tbody>
                </Table>
              ) : (
                <Text size="sm" c="dimmed">
                  No reconciliation data for this period.
                </Text>
              )}
            </Card>
          </SimpleGrid>

          <Card shadow="sm" radius="md" withBorder>
            <Group justify="space-between">
              <Title order={5}>Branch rollup</Title>
              <Text size="xs" c="dimmed">
                Click a row to expand per-BA detail
              </Text>
            </Group>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th />
                  <Table.Th>Branch</Table.Th>
                  <Table.Th ta="right">Sold</Table.Th>
                  <Table.Th ta="right">Commission</Table.Th>
                  <Table.Th ta="right">Performance</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {report.branch_reports.map((branch) => {
                  const open = openBranches.has(branch.branch_id)
                  return (
                    <>
                      <Table.Tr key={`b${branch.branch_id}`}>
                        <Table.Td>
                          <UnstyledButton onClick={() => toggleBranch(branch.branch_id)}>
                            {open ? <IconChevronUp size={16} /> : <IconChevronDown size={16} />}
                          </UnstyledButton>
                        </Table.Td>
                        <Table.Td>{branch.branch_name}</Table.Td>
                        <Table.Td ta="right">{branch.total_sales_count}</Table.Td>
                        <Table.Td ta="right">{formatMoney(branch.total_commission_owed)}</Table.Td>
                        <Table.Td ta="right">
                          <Badge color={Number(branch.performance_percentage) >= 100 ? 'teal' : 'yellow'} variant="light">
                            {formatPercent(branch.performance_percentage)}
                          </Badge>
                        </Table.Td>
                      </Table.Tr>
                      {open && (
                        <Table.Tr key={`b${branch.branch_id}-bas`}>
                          <Table.Td colSpan={5} bg="var(--mantine-color-gray-0)">
                            {branch.ba_summaries.length === 0 ? (
                              <Text size="sm" c="dimmed" px="md" py="xs">
                                No BA activity in this period.
                              </Text>
                            ) : (
                              <Table>
                                <Table.Thead>
                                  <Table.Tr>
                                    <Table.Th>BA</Table.Th>
                                    <Table.Th ta="right">Sales</Table.Th>
                                    <Table.Th ta="right">Commission</Table.Th>
                                    <Table.Th ta="right">Performance</Table.Th>
                                  </Table.Tr>
                                </Table.Thead>
                                <Table.Tbody>
                                  {branch.ba_summaries.map((ba) => (
                                    <Table.Tr key={ba.ba_id}>
                                      <Table.Td>{ba.ba_name}</Table.Td>
                                      <Table.Td ta="right">{ba.sales_count}</Table.Td>
                                      <Table.Td ta="right">{formatMoney(ba.commission_owed)}</Table.Td>
                                      <Table.Td ta="right">
                                        <Badge color={Number(ba.performance_percentage) >= 100 ? 'teal' : 'yellow'} variant="light">
                                          {formatPercent(ba.performance_percentage)}
                                        </Badge>
                                      </Table.Td>
                                    </Table.Tr>
                                  ))}
                                </Table.Tbody>
                              </Table>
                            )}
                          </Table.Td>
                        </Table.Tr>
                      )}
                    </>
                  )
                })}
              </Table.Tbody>
            </Table>

            {/* Recent Exports - Prominent Section */}
            {files.data && files.data.length > 0 && (
              <>
                <Group mt="md" mb="sm" justify="space-between">
                  <Text size="sm" fw={600}>
                    Recent exports:
                  </Text>
                  <Button size="xs" variant="subtle" onClick={() => files.refetch()}>
                    Refresh
                  </Button>
                </Group>
                <SimpleGrid cols={{ base: 1, md: 2 }}>
                  {files.data.slice(0, 4).map((f) => (
                    <Button
                      key={f.file_path}
                      size="xs"
                      variant="outline"
                      color={f.format === 'PDF' ? 'red' : 'green'}
                      onClick={() => downloadReportFile(f)}
                      fullWidth
                      leftSection={f.format === 'PDF' ? <IconChartBar size={14} /> : <IconReport size={14} />}
                    >
                      {f.format} · {formatDate(dayjs(f.created_at * 1000))}
                    </Button>
                  ))}
                </SimpleGrid>
              </>
            )}
          </Card>
        </>
      )}
    </Stack>
  )
}