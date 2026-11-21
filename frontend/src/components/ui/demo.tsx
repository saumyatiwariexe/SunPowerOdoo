import ComparisonBlock, { type SolarPackage } from "@/components/ui/comparison-3"

export default function ComparisonTableDemo({ packages }: { packages: SolarPackage[] }) {
  return <ComparisonBlock packages={packages} systemType="ON_GRID" />
}
