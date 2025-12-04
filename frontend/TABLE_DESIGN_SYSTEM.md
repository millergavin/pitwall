# Table Design System

A hybrid component architecture for building consistent, reusable table components across the application.

## Architecture Overview

```
┌─────────────────────────────────────────┐
│     Specialized Components              │
│  (Domain-specific, full-featured)       │
│                                         │
│  • ChampionshipDriverTable              │
│  • ChampionshipConstructorTable         │
│  • SessionResultsTable                  │
└─────────────────────────────────────────┘
                  ↓ uses
┌─────────────────────────────────────────┐
│       Table Primitives                  │
│  (Low-level building blocks)            │
│                                         │
│  • Table                                │
│  • TableHeader / TableHeaderCell        │
│  • TableBody                            │
│  • TableRow                             │
│  • TableCell                            │
└─────────────────────────────────────────┘
```

## When to Use What

### Use Specialized Components When:
- ✅ You're displaying championship standings (drivers or constructors)
- ✅ You're showing session results (race, qualifying, practice, sprint)
- ✅ You want built-in interactions (select/toggle, navigation)
- ✅ You want consistent formatting and behavior across pages

### Use Table Primitives When:
- ✅ You're building a unique table not covered by specialized components
- ✅ You need complete control over structure and styling
- ✅ You're prototyping a new table design
- ✅ The table has custom business logic

## Specialized Components

### ChampionshipDriverTable

Display driver championship standings with select/toggle interaction for filtering charts.

```tsx
import { ChampionshipDriverTable } from '../components/DataTable';

<ChampionshipDriverTable
  drivers={driverStandings}
  season={2025}
  selectedDriverIds={selectedDrivers}
  onToggleDriver={handleToggleDriver}
  onResetSelection={handleResetSelection}
  showPointsAdded={false}
/>
```

**Features:**
- Select/toggle rows to filter data
- Click header to reset selection
- Hover states for chart synchronization
- Automatic position numbering
- Team logo integration
- Conditional columns (points added)

### ChampionshipConstructorTable

Display constructor championship standings with same interaction pattern.

```tsx
import { ChampionshipConstructorTable } from '../components/DataTable';

<ChampionshipConstructorTable
  constructors={constructorStandings}
  season={2025}
  selectedConstructorIds={selectedConstructors}
  onToggleConstructor={handleToggleConstructor}
  onResetSelection={handleResetSelection}
/>
```

**Features:**
- Same interaction pattern as driver table
- Team logo integration
- Display name override support
- Cumulative points display

### SessionResultsTable

Display race, qualifying, or practice session results with navigation support.

```tsx
import { SessionResultsTable } from '../components/DataTable';

<SessionResultsTable
  results={classification}
  sessionType="race"
  title="2025 Abu Dhabi Grand Prix - Race Results"
  onDriverClick={(driverId) => navigate(`/drivers/${driverId}`)}
  showGridPosition={true}
  showPoints={true}
  showFastestLap={true}
/>
```

**Features:**
- Different layouts for race vs qualifying
- Grid position with position change indicators
- Time and gap formatting
- Fastest lap indicator
- Points display (race/sprint only)
- Click-to-navigate interaction
- Sticky header for long tables

## Table Primitives

### Basic Structure

```tsx
import {
  Table,
  TableHeader,
  TableHeaderCell,
  TableBody,
  TableRow,
  TableCell,
} from '../components/Table';

<Table variant="default">
  <TableHeader>
    <tr>
      <TableHeaderCell>Name</TableHeaderCell>
      <TableHeaderCell align="right">Value</TableHeaderCell>
    </tr>
  </TableHeader>
  <TableBody>
    {data.map((item) => (
      <TableRow key={item.id}>
        <TableCell>{item.name}</TableCell>
        <TableCell align="right" mono>{item.value}</TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

### Component Props

#### Table
- `variant`: `'default' | 'compact' | 'spacious'`
- `className`: Additional CSS classes

#### TableHeader
- `sticky`: Make header sticky on scroll
- `onClick`: Click handler (e.g., for reset selection)
- `title`: Tooltip text

#### TableHeaderCell
- `align`: `'left' | 'center' | 'right'`
- `width`: Fixed column width (e.g., "3rem", "100px")
- `className`: Additional CSS classes

#### TableRow
- `selected`: Highlight row as selected
- `faded`: Fade row when not selected
- `hoverable`: Enable hover effect (default: true)
- `onClick`: Click handler
- `onMouseEnter` / `onMouseLeave`: Hover handlers

#### TableCell
- `align`: `'left' | 'center' | 'right'`
- `mono`: Use monospace font
- `bold`: Bold text
- `size`: `'xs' | 'sm' | 'base' | 'lg'`
- `color`: `'white' | 'zinc-400' | 'zinc-500' | 'zinc-600'`
- `className`: Additional CSS classes

## Design Patterns

### Logo Integration

Team/constructor logos are integrated inline with names:

```tsx
<TableCell>
  <div className="flex items-center gap-2">
    {logo_url ? (
      <img src={logo_url} className="w-6 h-6 object-contain flex-shrink-0" />
    ) : (
      <div className="w-6 h-6 bg-zinc-800 rounded flex-shrink-0" />
    )}
    <span>{name}</span>
  </div>
</TableCell>
```

### Select/Toggle Pattern

Used in championship tables for filtering:

```tsx
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

const handleToggle = (id: string) => {
  setSelectedIds((prev) => {
    const newSet = new Set(prev);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    return newSet;
  });
};

const hasSelections = selectedIds.size > 0;

<TableRow
  selected={selectedIds.has(id)}
  faded={hasSelections && !selectedIds.has(id)}
  onClick={() => handleToggle(id)}
/>
```

### Navigation Pattern

Used in results tables for drilling down to details:

```tsx
<TableRow
  onClick={() => navigate(`/drivers/${driver.driver_id}`)}
  hoverable
>
  {/* row content */}
</TableRow>
```

## Styling Guidelines

### Colors
- **Headers**: `bg-zinc-950` with `text-zinc-400`
- **Row borders**: `border-zinc-900`
- **Hover**: `hover:bg-overlay-50`
- **Selected**: `bg-overlay-100`
- **Primary text**: `text-white`
- **Secondary text**: `text-zinc-400` / `text-zinc-500`

### Typography
- **Position numbers**: Monospace, small, zinc-500
- **Driver names**: Bold, white, larger last name
- **Acronyms**: Monospace, bold, zinc-500, smaller
- **Points**: Monospace, bold, white
- **Times/Gaps**: Monospace, right-aligned

### Spacing
- **Cell padding**: `px-2 py-2`
- **Logo size**: `w-6 h-6`
- **Gap between logo and text**: `gap-2`

## Testing Ground

Visit `/playground` to see all components in action with live examples and documentation.

## Adding New Specialized Components

When creating a new specialized table:

1. Create file in `/components/DataTable/`
2. Use Table primitives as building blocks
3. Handle domain-specific data transformation
4. Implement appropriate interaction patterns
5. Export from `/components/DataTable/index.ts`
6. Add example to Playground page

Example template:

```tsx
import { Table, TableHeader, TableHeaderCell, TableBody, TableRow, TableCell } from '../Table';

interface MyTableProps {
  data: MyDataType[];
  onRowClick?: (id: string) => void;
}

export const MyTable = ({ data, onRowClick }: MyTableProps) => {
  return (
    <Table>
      <TableHeader>
        {/* headers */}
      </TableHeader>
      <TableBody>
        {data.map((item) => (
          <TableRow key={item.id} onClick={() => onRowClick?.(item.id)}>
            {/* cells */}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
```

## Philosophy

This design system follows the **Hybrid Approach**:
- **80% code reuse** through primitives
- **100% clarity** through specialized components
- **Easy to extend** without breaking existing code
- **Clear separation** between structure and behavior

When in doubt, start with primitives in the Playground, then promote to a specialized component if the pattern repeats 3+ times across the app.

