import * as React from "react"
import { RiArrowRightLine, RiCheckLine, RiCloseLine, RiSparkling2Line } from "@remixicon/react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"

export type SolarPackage = {
  id: number
  name: string
  system_type: "ON_GRID" | "OFF_GRID" | null
  capacity_kw: number | null
  price_paise: number
  components: { product_name: string; category: string; qty: number }[]
}

type CellValue = boolean | string
type Feature = { label: string; values: CellValue[] }
type FeatureGroup = { section: string; features: Feature[] }

const money = (paise: number) => new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: paise % 100 ? 2 : 0,
}).format(paise / 100)

function Cell({ value, highlighted }: { value: CellValue; highlighted: boolean }) {
  if (typeof value === "boolean") return value ? (
    <span className={cn("mx-auto flex size-6 items-center justify-center rounded-full", highlighted ? "bg-brand-600" : "bg-brand-800")}>
      <RiCheckLine className="size-4 text-white" aria-hidden="true" />
      <span className="sr-only">Included</span>
    </span>
  ) : (
    <span className="mx-auto flex size-6 items-center justify-center rounded-full bg-brand-100">
      <RiCloseLine className="size-4 text-brand-700" aria-hidden="true" />
      <span className="sr-only">Not included</span>
    </span>
  )
  return <span className={cn("font-medium", highlighted ? "text-brand-900" : "text-brand-700")}>{value}</span>
}

const quantity = (plan: SolarPackage, category: string): CellValue => {
  const total = plan.components.filter((item) => item.category === category).reduce((sum, item) => sum + item.qty, 0)
  return total ? String(total) : false
}
const included = (plan: SolarPackage, category: string): boolean => plan.components.some((item) => item.category === category)

export default function ComparisonBlock({ packages, systemType }: { packages: SolarPackage[]; systemType: "ON_GRID" | "OFF_GRID" }) {
  const available = packages.filter((plan) => plan.system_type === systemType && plan.capacity_kw != null)
    .sort((a, b) => (a.capacity_kw || 0) - (b.capacity_kw || 0))
  const chosen = [available[0], available[Math.floor((available.length - 1) / 2)], available.at(-1)]
    .filter((plan): plan is SolarPackage => !!plan)
  const plans = [...new Map(chosen.map((plan) => [plan.id, plan])).values()]
  if (!plans.length) return <p className="state">No packages are available for this system type.</p>
  const featured = Math.floor((plans.length - 1) / 2)
  const groups: FeatureGroup[] = [
    { section: "System", features: [
      { label: "Capacity", values: plans.map((p) => `${p.capacity_kw} kW`) },
      { label: "Solar panels", values: plans.map((p) => quantity(p, "PANEL")) },
      { label: "Inverter", values: plans.map((p) => included(p, "INVERTER")) },
      { label: "Battery units", values: plans.map((p) => quantity(p, "BATTERY")) },
    ] },
    { section: "Equipment & work", features: [
      { label: "Mounting stands", values: plans.map((p) => quantity(p, "STAND")) },
      { label: "Charge controller", values: plans.map((p) => included(p, "CHARGE_CONTROLLER")) },
      { label: "Wiring & safety", values: plans.map((p) => included(p, "WIRING") && included(p, "SAFETY")) },
      { label: "Installation service", values: plans.map((p) => included(p, "SERVICE")) },
    ] },
  ]

  return <section className="comparison-block" aria-label={`${systemType === "ON_GRID" ? "On-grid" : "Off-grid"} package comparison`}>
    <div className="comparison-heading">
      <Badge variant="outline"><RiSparkling2Line className="size-4" aria-hidden="true" /> Compare plans</Badge>
      <h3>See what changes as you size up.</h3>
      <p>These prices and equipment counts come from the current catalog. Your approved survey determines the final quote.</p>
    </div>
    <p className="comparison-swipe">Swipe sideways to compare all sizes <RiArrowRightLine className="size-4" aria-hidden="true" /></p>
    <div className="comparison-scroll" tabIndex={0} role="region" aria-label="Scroll to compare solar plans">
      <Table className="comparison-table">
        <TableHeader><TableRow>
          <TableHead scope="col" className="comparison-feature-col">Included</TableHead>
          {plans.map((plan, i) => <TableHead scope="col" key={plan.id} className={cn("comparison-plan-head", i === featured && "comparison-highlight")}>
            {i === featured && <Badge variant="default">Featured size</Badge>}
            <strong>{plan.capacity_kw} kW</strong><span>{plan.name}</span><b>{money(plan.price_paise)}</b>
          </TableHead>)}
        </TableRow></TableHeader>
        <TableBody>
          {groups.map((group) => <React.Fragment key={group.section}>
            <TableRow className="comparison-group"><TableCell colSpan={plans.length + 1}>{group.section}</TableCell></TableRow>
            {group.features.map((feature) => <TableRow key={feature.label}>
              <TableHead scope="row">{feature.label}</TableHead>
              {feature.values.map((value, i) => <TableCell key={plans[i].id} className={cn("text-center", i === featured && "comparison-highlight")}><Cell value={value} highlighted={i === featured} /></TableCell>)}
            </TableRow>)}
          </React.Fragment>)}
          <TableRow className="comparison-action-row"><TableCell />
            {plans.map((plan, i) => <TableCell key={plan.id} className={cn("text-center", i === featured && "comparison-highlight")}>
              <Button asChild variant={i === featured ? "default" : "outline"} size="sm">
                <a href={`/enquiry?kw=${plan.capacity_kw}&type=${systemType}`}>Enquire <RiArrowRightLine className="size-4" aria-hidden="true" /></a>
              </Button>
            </TableCell>)}
          </TableRow>
        </TableBody>
      </Table>
    </div>
    <p className="comparison-note">Counts reflect catalog package contents. Prices are indicative; site conditions and approved changes can alter the final quote.</p>
  </section>
}
