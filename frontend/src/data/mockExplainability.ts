import type { ExplainabilityEntry, ADRPreview } from '@/types/dashboard';

export const explainabilityEntries: ExplainabilityEntry[] = [
  {
    id: 'ex1',
    service: 'NotificationService',
    primaryReason: 'Low coupling (95), independent database access, async-ready architecture',
    secondaryReasons: [
      'No circular dependencies detected',
      'Clean interface boundaries',
      'Already uses message queue for some operations',
    ],
    evidence: {
      codeIsolation: '99 — Fully isolated module with clean imports',
      lowCoupling: '92 — Minimal external dependencies',
      databaseIndependence: '95 — Own notification_logs table, no shared schema',
      businessAlignment: '80 — Clear single responsibility for communications',
    },
    tradeoffs: {
      pros: ['Enables async architecture', 'Independent scaling during peak', 'Technology flexibility for channels'],
      cons: ['Additional infrastructure cost', 'Eventual consistency complexity', 'Team needs messaging expertise'],
    },
    alternatives: ['Shared notification library', 'Third-party service (SNS/SES)'],
    impact: {
      business: 'Real-time multi-channel notifications improve customer engagement by 25%',
      technical: 'Low complexity, 2-3 weeks, standard async patterns',
      risk: 'Low — well-understood pattern with AWS-native tools',
    },
    confidence: 95,
    confidenceFactors: [
      { id: 'cf1', name: 'Code Isolation', score: 99, weight: 30, description: 'Module is cleanly isolated' },
      { id: 'cf2', name: 'Low Coupling', score: 92, weight: 25, description: 'Minimal external dependencies' },
      { id: 'cf3', name: 'DB Independence', score: 95, weight: 25, description: 'Own data store' },
      { id: 'cf4', name: 'Business Fit', score: 80, weight: 20, description: 'Clear business capability' },
    ],
  },
  {
    id: 'ex2',
    service: 'OrderManagementService',
    primaryReason: 'God class detected (2,400 LOC), 85% coupling, multiple responsibilities',
    secondaryReasons: [
      'Handles orders, fulfillment, tracking, and returns',
      'Circular dependency with PaymentService',
      'Requires careful decomposition strategy',
    ],
    evidence: {
      codeIsolation: '35 — Heavily intertwined with other modules',
      lowCoupling: '20 — 85% coupling score, circular deps detected',
      databaseIndependence: '40 — Shares orders DB with 3 other services',
      businessAlignment: '55 — Mixes multiple business capabilities',
    },
    tradeoffs: {
      pros: ['Unblocks other service extractions', 'Reduces change failure rate by 60%', 'Enables team autonomy'],
      cons: ['High implementation risk', 'Requires domain expertise', '6-8 weeks minimum effort'],
    },
    alternatives: ['Strangler fig pattern', 'Branch by abstraction', 'Parallel run'],
    impact: {
      business: 'Critical path — blocks full microservices adoption',
      technical: 'High complexity, requires domain-driven design expertise',
      risk: 'High — largest and most complex extraction',
    },
    confidence: 88,
    confidenceFactors: [
      { id: 'cf5', name: 'Code Isolation', score: 35, weight: 30, description: 'Needs significant refactoring' },
      { id: 'cf6', name: 'Low Coupling', score: 20, weight: 25, description: 'Heavily coupled' },
      { id: 'cf7', name: 'DB Independence', score: 40, weight: 25, description: 'Shared database' },
      { id: 'cf8', name: 'Business Fit', score: 55, weight: 20, description: 'Multiple responsibilities' },
    ],
  },
  {
    id: 'ex3',
    service: 'PaymentService',
    primaryReason: 'Moderate isolation (65), critical for compliance, requires PCI scope reduction',
    secondaryReasons: [
      'Handles sensitive payment data',
      'Circular dependency with OrderService',
      'Needs dedicated security review',
    ],
    evidence: {
      codeIsolation: '60 — Partially isolated, some shared utilities',
      lowCoupling: '45 — Circular dependency with OrderService',
      databaseIndependence: '55 — Own payment_records table but shared schema',
      businessAlignment: '75 — Clear payment processing responsibility',
    },
    tradeoffs: {
      pros: ['Reduces PCI compliance scope', 'Enables independent security reviews', 'Faster payment feature delivery'],
      cons: ['PCI compliance requirements', 'Requires secure API design', 'Cross-service transaction handling'],
    },
    alternatives: ['Stripe/PayPal abstraction', 'Shared payment library'],
    impact: {
      business: 'Reduces compliance cost by 40%, enables payment method flexibility',
      technical: 'Medium complexity, requires security-first design',
      risk: 'Medium — compliance requirements add complexity',
    },
    confidence: 70,
    confidenceFactors: [
      { id: 'cf9', name: 'Code Isolation', score: 60, weight: 30, description: 'Partially isolated' },
      { id: 'cf10', name: 'Low Coupling', score: 45, weight: 25, description: 'Circular dependency present' },
      { id: 'cf11', name: 'DB Independence', score: 55, weight: 25, description: 'Shared schema' },
      { id: 'cf12', name: 'Business Fit', score: 75, weight: 20, description: 'Clear responsibility' },
    ],
  },
  {
    id: 'ex4',
    service: 'InventoryService',
    primaryReason: 'Good isolation (85), low coupling, clean database boundaries',
    secondaryReasons: [
      'Self-contained stock management',
      'Event-driven updates work well',
      'Clear API surface',
    ],
    evidence: {
      codeIsolation: '88 — Well-structured module with clean interfaces',
      lowCoupling: '82 — Few dependencies, mostly read-only',
      databaseIndependence: '85 — Own inventory schema, no cross-service writes',
      businessAlignment: '82 — Clear inventory management responsibility',
    },
    tradeoffs: {
      pros: ['Independent scaling for stock operations', 'Clear ownership model', 'Easy to monitor'],
      cons: ['Additional service to maintain', 'Eventual consistency for stock levels'],
    },
    alternatives: ['Shared inventory module', 'Database views'],
    impact: {
      business: 'Real-time stock visibility improves order accuracy by 15%',
      technical: 'Low complexity, standard CRUD with events',
      risk: 'Low — well-understood domain',
    },
    confidence: 88,
    confidenceFactors: [
      { id: 'cf13', name: 'Code Isolation', score: 88, weight: 30, description: 'Well-structured module' },
      { id: 'cf14', name: 'Low Coupling', score: 82, weight: 25, description: 'Few dependencies' },
      { id: 'cf15', name: 'DB Independence', score: 85, weight: 25, description: 'Own schema' },
      { id: 'cf16', name: 'Business Fit', score: 82, weight: 20, description: 'Clear responsibility' },
    ],
  },
];

export const adrPreviews: ADRPreview[] = [
  {
    id: 'ADR-001',
    title: 'Extract NotificationService as Independent Microservice',
    status: 'accepted',
    context: 'NotificationService has 90% readiness score with low coupling. Current monolithic implementation limits notification channel flexibility and prevents independent scaling during peak traffic periods.',
    decision: 'Extract NotificationService as an independent microservice using AWS SQS for async messaging and SES for email delivery. Implement event-driven architecture for real-time notifications.',
    consequences: {
      positive: ['Independent scaling', 'Multi-channel support', 'Technology flexibility'],
      negative: ['Additional infrastructure', 'Eventual consistency'],
      risks: ['Message ordering guarantees', 'Delivery failure handling'],
    },
    alternatives: ['Shared notification library', 'Third-party SaaS (Twilio)'],
    confidence: 95,
    service: 'NotificationService',
  },
  {
    id: 'ADR-002',
    title: 'Decompose OrderManagementService God Class',
    status: 'proposed',
    context: 'OrderManagementService is a god class with 2,400 LOC and 85% coupling. It handles order creation, fulfillment, tracking, and returns — violating single responsibility principle.',
    decision: 'Decompose into three focused services: OrderService (creation/validation), FulfillmentService (shipping/warehouse), and TrackingService (status/notifications).',
    consequences: {
      positive: ['Single responsibility', 'Independent deployment', 'Team autonomy'],
      negative: ['Migration complexity', 'Data consistency challenges'],
      risks: ['Breaking change propagation', 'Testing coverage gaps'],
    },
    alternatives: ['Strangler fig pattern', 'Branch by abstraction'],
    confidence: 88,
    service: 'OrderManagementService',
  },
  {
    id: 'ADR-003',
    title: 'Break Payment-Order Circular Dependency',
    status: 'proposed',
    context: 'PaymentService and OrderService have a circular dependency chain. PaymentService calls OrderService for status updates, while OrderService calls PaymentService for processing.',
    decision: 'Introduce an event-driven pattern using AWS EventBridge. Orders emit OrderCreated events, Payments subscribe and process. Payments emit PaymentProcessed events, Orders update status.',
    consequences: {
      positive: ['Breaks circular dependency', 'Event-driven scalability', 'Loose coupling'],
      negative: ['Eventual consistency', 'Event schema management'],
      risks: ['Event ordering', 'Dead letter queue management'],
    },
    alternatives: ['Shared interface extraction', 'API Gateway mediation'],
    confidence: 92,
    service: 'PaymentService',
  },
  {
    id: 'ADR-004',
    title: 'Implement API Gateway for Cross-Cutting Concerns',
    status: 'proposed',
    context: 'Currently no centralized management for authentication, rate limiting, or request routing. Each service handles these independently, leading to inconsistency.',
    decision: 'Deploy AWS API Gateway as the single entry point. Implement JWT authentication, rate limiting, request/response transformation, and API versioning at the gateway level.',
    consequences: {
      positive: ['Centralized security', 'Consistent rate limiting', 'API versioning'],
      negative: ['Single point of failure', 'Additional latency'],
      risks: ['Gateway misconfiguration', 'Over-centralization'],
    },
    alternatives: ['Service mesh (Istio)', 'BFF pattern'],
    confidence: 75,
    service: 'System-wide',
  },
];
