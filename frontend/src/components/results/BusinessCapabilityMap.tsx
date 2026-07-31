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
  'Course Management': 'Truck',
  'Employee Management': 'Users',
  'Feedback Management': 'Bell',
};

const colorMap: Record<string, string> = {
  'Customer Communication': 'bg-blue-500',
  'Supply Chain Management': 'bg-green-500',
  'User Management': 'bg-purple-500',
  'Financial Operations': 'bg-yellow-500',
  'Order Management': 'bg-orange-500',
  'Course Management': 'bg-teal-500',
  'Employee Management': 'bg-indigo-500',
  'Feedback Management': 'bg-pink-500',
};

export function BusinessCapabilityMap({ services }: { services: ServiceBoundary[] }) {
  const capabilities: BusinessCapability[] = services.reduce(
    (acc: BusinessCapability[], svc) => {
      const name = svc.business_capability || 'Core Application';
      const exists = acc.find((c) => c.name === name);
      if (exists) {
        exists.classes += svc.classes.length;
        exists.readiness = Math.min(exists.readiness, mapApiServiceToCapability(svc).readiness);
        exists.confidence = Math.max(exists.confidence, svc.confidence || 0);
        return acc;
      }
      const mapped = mapApiServiceToCapability(svc);
      acc.push({
        id: `cap-${name.replace(/\s+/g, '-').toLowerCase()}`,
        name,
        description:
          svc.description ||
          `${name} capability identified across the application`,
        readiness: mapped.readiness,
        confidence: mapped.confidence,
        risk: mapped.risk,
        classes: mapped.classes,
        recommendedService: svc.name,
        color: colorMap[name] || 'bg-gray-500',
        icon: iconMap[name] || 'Layers',
      });
      return acc;
    },
    [],
  );

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
