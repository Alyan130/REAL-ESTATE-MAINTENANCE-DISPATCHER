## Architecture: Front-End Redesign (Notion Warm Workspace)

```mermaid
graph TD
    subgraph Design System Tokens
        G[globals.css] -->|Theme Variables| Palette[Notion Warm Neutrals & Azul Notion]
        G -->|Shapes| Radius[Pills 9999px & Rounded 2xl]
        G -->|Borders & Depth| Borders[Whisper Borders & Multi-layer Shadows]
    end

    subgraph Core UI Components
        Button[button.tsx]
        Card[card.tsx]
        Badge[badge.tsx]
        Field[field.tsx]
        Modal[modal.tsx]
        Alert[alert.tsx]
        EmptyState[empty-state.tsx]
        Skeleton[skeleton.tsx]
        PageHeader[page-header.tsx]
    end

    subgraph Layout Components
        AppShell[app-shell.tsx]
        AuthLayout[auth-layout.tsx]
    end

    subgraph Feature Components
        TicketRow[ticket-row.tsx]
        StatusBadge[status-badge.tsx]
        TicketFilters[ticket-filters.tsx]
        PhotoGrid[photo-grid.tsx]
        PropertyModals[add-property-modal.tsx]
        TenantModals[invite-tenant-modal.tsx]
        VendorModals[invite-vendor-modal.tsx]
    end

    subgraph App Pages
        LandingPage[app/page.tsx]
        LoginPage[app/login/page.tsx]
        InvitePage[app/accept-invite/page.tsx]
        PMDashboard[app/(pm)/dashboard/page.tsx]
        PMTickets[app/(pm)/tickets/[id]/page.tsx]
        PMProperties[app/(pm)/properties/page.tsx]
        PMTenants[app/(pm)/tenants/page.tsx]
        PMVendors[app/(pm)/vendors/page.tsx]
        TenantTickets[app/(tenant)/my-tickets/page.tsx]
        VendorPage[app/vendor/page.tsx]
    end

    Palette --> Core UI Components
    Radius --> Core UI Components
    Borders --> Core UI Components

    Core UI Components --> Layout Components
    Core UI Components --> Feature Components
    Layout Components --> App Pages
    Feature Components --> App Pages
```
