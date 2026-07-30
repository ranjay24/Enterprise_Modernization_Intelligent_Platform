import type { ServiceBoundary } from '@/types/api';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { CapabilityCard } from '@/components/cards/CapabilityCard';
import { mapApiServiceToCapability } from '@/types/results';
import type { BusinessCapability } from '@/types/dashboard';

const iconMap: Record<string, string> = {
  'Customer Communication': 'Bell',
  'Supply Chain Management': 'Package',
  'User Management': 'Users',
  'Financial Operations': 'CreditCard',
  'Order Management': 'ShoppingCart',
};

const colorMap: Record<string, string> = {
  'Customer Communication': 'bg-blue-500',
  'Supply Chain Management': 'bg-green-500',
  'User Management': 'bg-purple-500',
  'Financial Operations': 'bg-yellow-500',
  'Order Management': 'bg-orange-500',
};

export function BusinessCapabilityMap({ services }: { services: ServiceBoundary[] }) {
  const capabilities: BusinessCapability[] = services
    .filter((s) => s.business_capability)
    .reduce((acc: BusinessCapability[], svc) => {
      const exists = acc.find((c) => c.name === svc.business_capability);
      if (exists) {
        exists.classes += svc.classes.length;
        exists.readiness = Math.min(exists.readiness, mapApiServiceToCapability(svc).readiness);
        return acc;
      }
      const mapped = mapApiServiceToCapability(svc);
      acc.push({
        id: `cap-${svc.name}`,
        name: svc.business_capability!,
        description: svc.description,
        readiness: mapped.readiness,
        confidence: mapped.confidence,
        risk: mapped.risk,
        classes: mapped.classes,
        recommendedService: svc.name,
        color: colorMap[svc.business_capability!] || 'bg-gray-500',
        icon: iconMap[svc.business_capability!] || 'Layers',
      });
      return acc;
    }, []);

  return (
    <section>
      <SectionHeader
        title="Business Capability Map"
        description={`${capabilities.length} business capabilities identified`}
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {capabilities.map((cap) => (
          <CapabilityCard key={cap.id} data={cap} />
        ))}
      </div>
    </section>
  );
}
