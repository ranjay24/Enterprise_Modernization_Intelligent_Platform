import type { MigrationWave } from '@/types/api';

export type AwsCategory =
  | 'gateway'
  | 'compute'
  | 'database'
  | 'messaging'
  | 'observability'
  | 'storage'
  | 'security'
  | 'other';

export function awsCategory(name: string): AwsCategory {
  const n = name.toLowerCase();
  if (n.includes('api gateway')) return 'gateway';
  if (n.includes('lambda') || n.includes('ecs') || n.includes('fargate') || n.includes('ec2') || n.includes('eks') || n.includes('app runner')) return 'compute';
  if (n.includes('rds') || n.includes('dynamo') || n.includes('aurora') || n.includes('documentdb') || n.includes('neptune') || n.includes('elasticache') || n.includes('redshift') || n.includes('opensearch')) return 'database';
  if (n.includes('sns') || n.includes('sqs') || n.includes('msk') || n.includes('kafka') || n.includes('eventbridge') || n.includes('kinesis') || n.includes('amazon mq') || n.includes('rabbit')) return 'messaging';
  if (n.includes('cloudwatch') || n.includes('x-ray') || n.includes('cloudtrail')) return 'observability';
  if (n.includes('s3') || n.includes('efs') || n.includes('ebs') || n.includes('glacier')) return 'storage';
  if (n.includes('secrets') || n.includes('iam') || n.includes('kms') || n.includes('waf') || n.includes('guardduty') || n.includes('shield')) return 'security';
  return 'other';
}

export interface AwsInventoryEntry {
  service_name: string;
  use_case: string;
  category: AwsCategory;
  count: number;
  microservices: string[];
  waves: number[];
}

export function buildAwsInventory(waves: MigrationWave[]): AwsInventoryEntry[] {
  const map = new Map<string, AwsInventoryEntry>();
  for (const wave of waves) {
    for (const [svcName, recs] of Object.entries(wave.aws_recommendations ?? {})) {
      for (const rec of recs) {
        const existing = map.get(rec.service_name);
        if (existing) {
          if (!existing.microservices.includes(svcName)) existing.microservices.push(svcName);
          if (!existing.waves.includes(wave.wave_number)) existing.waves.push(wave.wave_number);
          existing.count += 1;
        } else {
          map.set(rec.service_name, {
            service_name: rec.service_name,
            use_case: rec.use_case,
            category: awsCategory(rec.service_name),
            count: 1,
            microservices: [svcName],
            waves: [wave.wave_number],
          });
        }
      }
    }
  }
  return Array.from(map.values()).sort((a, b) => b.count - a.count);
}
