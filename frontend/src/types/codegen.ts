export interface CodeGenService {
  id: string;
  name?: string;
  business_capability?: string;
  source_boundary?: string;
  tech_stack?: string[];
  broker_role?: 'kafka' | 'rabbitmq' | 'both' | 'none';
  broker_rationale?: string;
  resilience?: string[];
  database?: { engine?: string; name?: string; tables?: string[] };
  package?: string;
  source_classes?: string[];
  exposed_endpoints?: { method?: string; path?: string; dto_in?: string; dto_out?: string }[];
  internal_endpoints?: { method?: string; path?: string }[];
  feign_clients?: { name?: string; target_service?: string; endpoints?: { method?: string; path?: string }[] }[];
  events?: {
    publishes?: { topic?: string; payload?: { fields?: string[] } }[];
    subscribes?: { topic?: string; consumer_group?: string; queue?: string }[];
  };
  server_port?: number | string;
}

export interface ArchitectureNode {
  id: string;
  type: 'gateway' | 'service' | 'database' | 'broker';
  label?: string;
  subtype?: string;
  broker_role?: string;
  resilience?: string[];
  tech_stack?: string[];
}

export interface ArchitectureEdge {
  id: string;
  source: string;
  target: string;
  type: 'rest' | 'feign' | 'database' | 'publish' | 'subscribe' | 'queue';
  label?: string;
}

export interface MessageTopology {
  topics?: { name?: string; producer?: string; consumers?: string[] }[];
  queues?: { name?: string; producer?: string; consumer?: string }[];
}

export interface ArchitectureDesign {
  version?: string;
  services?: CodeGenService[];
  nodes?: ArchitectureNode[];
  edges?: ArchitectureEdge[];
  message_topology?: MessageTopology;
  generated_services?: string[];
  iteration?: number;
  approved?: boolean;
  fallback?: boolean;
}

export interface CodeGenWave {
  wave?: number;
  name?: string;
  services?: string[];
  rationale?: string;
}

export interface CodeGenPlan {
  version?: string;
  waves?: CodeGenWave[];
  services?: Record<string, CodeGenService> | CodeGenService[];
  global_config?: Record<string, string>;
}

export interface CodeGenFile {
  path: string;
  content: string;
}

export interface ServiceCode {
  service_id?: string;
  base_package?: string;
  language?: string;
  build_tool?: string;
  files?: CodeGenFile[];
  compilation_notes?: string;
  deployment_notes?: string;
}

export interface ReviewFinding {
  id?: string;
  severity?: 'critical' | 'major' | 'minor' | 'info';
  category?: string;
  file?: string;
  finding?: string;
  recommendation?: string;
}

export interface ReviewReport {
  service_id?: string;
  iteration?: number;
  approved?: boolean;
  summary?: string;
  score?: number;
  findings?: ReviewFinding[];
}

export interface CodeGenStatus {
  job_id: string;
  in_progress: boolean;
  progress: number;
  current_stage: string;
  summary: {
    status?: string;
    iterations?: number;
    services_generated?: string[];
    approved?: boolean;
  } | null;
  review: ReviewReport | null;
  services_generated: string[];
}

export interface CodeGenCodeResponse {
  job_id: string;
  services: Record<string, ServiceCode>;
}
