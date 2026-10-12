import {
  AppShell,
  Badge,
  Group,
  NavLink,
  Text,
  UnstyledButton,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import {
  IconChartBar,
  IconLogout,
  IconReport,
  IconSettings,
  IconTruck,
} from '@tabler/icons-react'
import { NavLink as RouterNavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'

const links = [
  { to: '/', label: 'Dashboard', icon: IconChartBar, end: true },
  { to: '/stock', label: 'Stock', icon: IconTruck },
  { to: '/reconciliation', label: 'Reconciliation', icon: IconReport },
  { to: '/management', label: 'Management', icon: IconSettings },
]

export default function AppLayout() {
  const [opened, { toggle }] = useDisclosure()
  const { user, logout } = useAuth()

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <UnstyledButton
              onClick={toggle}
              hiddenFrom="sm"
              aria-label="Toggle navigation"
            >
              <Text size="lg">☰</Text>
            </UnstyledButton>
            <Text fw={700}>SIM Stock &amp; Sales</Text>
            <Badge color="teal" variant="light">
              HQ
            </Badge>
          </Group>
          <Group gap="xs">
            <Text size="sm" c="dimmed">
              {user?.email}
            </Text>
            <UnstyledButton onClick={logout} aria-label="Sign out">
              <IconLogout size={18} />
            </UnstyledButton>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            component={RouterNavLink}
            label={link.label}
            leftSection={<link.icon size={18} />}
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  )
}