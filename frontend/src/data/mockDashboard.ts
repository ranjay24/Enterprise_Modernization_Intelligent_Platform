import type {
  KPICard,
  ReadinessBreakdown,
  ConfidenceBreakdown,
  HealthMetric,
  ServiceReadiness,
  MigrationTimelineWave,
  AIRecommendation,
  DebtItem,
  CostBreakdownData,
  ChartDataPoint,
  RecentAnalysis,
  QuickAction,
} from '@/types/dashboard';

export const kpiCards: KPICard[] = [
  {
    id: 'readiness',
    title: 'Overall Readiness',
    value: 84,
    unit: '%',
    description: 'Modernization readiness score',
    trend: { value: 12, label: 'vs last quarter', direction: 'up' },
    icon: 'Target',
    color: 'blue',
    status: 'good',
  },
  {
    id: 'risk',
    title: 'Risk Level',
    value: 'Medium',
    description: 'Overall migration risk assessment',
    trend: { value: 0, label: 'stable', direction: 'neutral' },
    icon: 'Shield',
    color: 'yellow',
    status: 'warning',
  },
  {
    id: 'confidence',
    title: 'AI Confidence',
    value: 91,
    unit: '%',
    description: 'Analysis confidence level',
    trend: { value: 3, label: 'improving', direction: 'up' },
    icon: 'Brain',
    color: 'green',
    status: 'good',
  },
  {
    id: 'complexity',
    title: 'Migration Complexity',
    value: 'Moderate',
    description: 'Estimated implementation complexity',
    trend: { value: 0, label: 'assessed', direction: 'neutral' },
    icon: 'Layers',
    color: 'yellow',
    status: 'warning',
  },
  {
    id: 'savings',
    title: 'Monthly Savings',
    value: '$4,200',
    unit: '/mo',
    description: 'Projected infrastructure savings',
    trend: { value: 15, label: 'projected', direction: 'up' },
    icon: 'DollarSign',
    color: 'green',
    status: 'good',
  },
];

export const readinessBreakdown: ReadinessBreakdown = {
  overall: 34,
  confidence: 85,
  dimensions: [
    { id: 'cq', name: 'Code Quality', score: 30, weight: 25, evidence: 'High coupling between classes, god class detected in OrderManagement', status: 'critical', icon: 'Code2' },
    { id: 'arch', name: 'Architecture', score: 50, weight: 20, evidence: 'Mixed MVC and layered patterns, unclear domain boundaries', status: 'warning', icon: 'Building2' },
    { id: 'cloud', name: 'Cloud Readiness', score: 30, weight: 20, evidence: 'Stateful sessions, file-based config, no health checks', status: 'critical', icon: 'Cloud' },
    { id: 'sep', name: 'Service Separation', score: 40, weight: 20, evidence: '3 circular dependency chains detected between Order-Payment-Cart', status: 'warning', icon: 'GitBranch' },
    { id: 'db', name: 'Database Coupling', score: 50, weight: 10, evidence: 'Shared database across all modules, no schema isolation', status: 'warning', icon: 'Database' },
    { id: 'doc', name: 'Documentation', score: 20, weight: 5, evidence: 'Only 35% of classes have Javadoc, no API documentation', status: 'critical', icon: 'FileText' },
  ],
};

export const confidenceBreakdown: ConfidenceBreakdown = {
  overall: 85,
  factors: [
    { id: 'data_quality', name: 'Data Quality', score: 90, weight: 30, description: 'Static analysis data is comprehensive and reliable' },
    { id: 'pattern_match', name: 'Pattern Matching', score: 88, weight: 25, description: 'Service boundaries align with detected code patterns' },
    { id: 'domain_fit', name: 'Domain Fit', score: 82, weight: 20, description: 'Recommendations match business domain structure' },
    { id: 'historical', name: 'Historical Accuracy', score: 78, weight: 15, description: 'Similar projects validated these assessment criteria' },
    { id: 'complexity', name: 'Complexity Estimation', score: 85, weight: 10, description: 'Effort estimates within 20% of actual for similar projects' },
  ],
};

export const healthMetrics: HealthMetric[] = [
  { id: 'candidates', title: 'Microservice Candidates', value: 12, maxValue: 15, unit: '', status: 'healthy', description: 'Classes identified as potential microservice boundaries', icon: 'Puzzle' },
  { id: 'deps', title: 'Dependency Health', value: 78, maxValue: 100, unit: '/100', status: 'healthy', description: 'Overall dependency management score', icon: 'Link' },
  { id: 'quality', title: 'Architecture Quality', value: 65, maxValue: 100, unit: '/100', status: 'warning', description: 'Architectural pattern consistency and best practices', icon: 'Layout' },
  { id: 'maintain', title: 'Maintainability Index', value: 72, maxValue: 100, unit: '/100', status: 'healthy', description: 'Code maintainability based on complexity metrics', icon: 'Wrench' },
  { id: 'debt', title: 'Technical Debt Score', value: 38, maxValue: 100, unit: '/100', status: 'warning', description: 'Estimated technical debt impact on velocity', icon: 'AlertTriangle' },
  { id: 'complexity', title: 'Code Complexity', value: 42, maxValue: 100, unit: '/100', status: 'warning', description: 'Average cyclomatic complexity across codebase', icon: 'Activity' },
];

export const serviceReadiness: ServiceReadiness[] = [
  { id: 'ns', name: 'NotificationService', readiness: 'green', risk: 'low', confidence: 93, cohesion: 92, coupling: 15, classes: 3, status: 'ready' },
  { id: 'is', name: 'InventoryService', readiness: 'green', risk: 'low', confidence: 88, cohesion: 85, coupling: 22, classes: 5, status: 'ready' },
  { id: 'us', name: 'UserService', readiness: 'green', risk: 'low', confidence: 91, cohesion: 88, coupling: 18, classes: 6, status: 'ready' },
  { id: 'ss', name: 'ShippingService', readiness: 'yellow', risk: 'medium', confidence: 76, cohesion: 72, coupling: 35, classes: 4, status: 'needs_work' },
  { id: 'ps', name: 'PaymentService', readiness: 'yellow', risk: 'medium', confidence: 70, cohesion: 68, coupling: 42, classes: 6, status: 'needs_work' },
  { id: 'cs', name: 'CartService', readiness: 'yellow', risk: 'medium', confidence: 74, cohesion: 75, coupling: 38, classes: 5, status: 'needs_work' },
  { id: 'pts', name: 'ProductService', readiness: 'yellow', risk: 'medium', confidence: 72, cohesion: 70, coupling: 40, classes: 7, status: 'needs_work' },
  { id: 'os', name: 'OrderService', readiness: 'red', risk: 'high', confidence: 58, cohesion: 55, coupling: 65, classes: 8, status: 'not_ready' },
  { id: 'oms', name: 'OrderManagementService', readiness: 'red', risk: 'high', confidence: 35, cohesion: 40, coupling: 85, classes: 14, status: 'not_ready' },
];

export const migrationWaves: MigrationTimelineWave[] = [
  {
    id: 'w1', wave: 1, name: 'Foundation', priority: 'high',
    duration: 'Weeks 1-4', durationWeeks: { start: 1, end: 4 },
    services: ['NotificationService', 'InventoryService', 'UserService'],
    risk: 'low', status: 'completed', progress: 100,
    dependencies: [], estimatedEngineers: 2, estimatedCost: 16000,
  },
  {
    id: 'w2', wave: 2, name: 'Core Services', priority: 'critical',
    duration: 'Weeks 5-10', durationWeeks: { start: 5, end: 10 },
    services: ['PaymentService', 'CartService', 'ProductService'],
    risk: 'medium', status: 'in_progress', progress: 45,
    dependencies: ['w1'], estimatedEngineers: 3, estimatedCost: 36000,
  },
  {
    id: 'w3', wave: 3, name: 'Integration', priority: 'high',
    duration: 'Weeks 11-18', durationWeeks: { start: 11, end: 18 },
    services: ['ShippingService', 'OrderService'],
    risk: 'medium', status: 'planned', progress: 0,
    dependencies: ['w2'], estimatedEngineers: 3, estimatedCost: 48000,
  },
  {
    id: 'w4', wave: 4, name: 'Complex Extraction', priority: 'critical',
    duration: 'Weeks 19-28', durationWeeks: { start: 19, end: 28 },
    services: ['OrderManagementService'],
    risk: 'high', status: 'planned', progress: 0,
    dependencies: ['w3'], estimatedEngineers: 4, estimatedCost: 80000,
  },
];

export const aiRecommendations: AIRecommendation[] = [
  {
    id: 'r1', title: 'Extract NotificationService First',
    recommendation: 'NotificationService has the highest readiness (90%) with low coupling. Extract as independent microservice using async messaging.',
    businessValue: 'Enables real-time notifications across channels, improving customer engagement by 25%',
    technicalImpact: 'Low complexity, 2-3 weeks effort, minimal risk',
    confidence: 95, priority: 'critical', category: 'architecture',
    effort: '2-3 weeks', impact: 'high',
    evidence: ['92% cohesion score', 'No circular dependencies', 'Independent database access'],
  },
  {
    id: 'r2', title: 'Break Order-Payment Circular Dependency',
    recommendation: 'OrderService and PaymentService have a circular dependency chain. Introduce an event-driven pattern to break the cycle.',
    businessValue: 'Reduces deployment risk and enables independent scaling during peak traffic',
    technicalImpact: 'Medium complexity, requires event bus implementation',
    confidence: 91, priority: 'high', category: 'architecture',
    effort: '3-4 weeks', impact: 'high',
    evidence: ['Circular dependency detected', '65% coupling score', 'Event-driven pattern recommended'],
  },
  {
    id: 'r3', title: 'Decompose OrderManagementService God Class',
    recommendation: 'OrderManagementService has 2,400 LOC across 14 classes. Decompose into Order, Fulfillment, and Tracking services.',
    businessValue: 'Reduces change failure rate by 60% and accelerates feature delivery',
    technicalImpact: 'High complexity, requires careful domain boundary analysis',
    confidence: 88, priority: 'high', category: 'architecture',
    effort: '6-8 weeks', impact: 'high',
    evidence: ['2,400 LOC god class', '14 tightly coupled classes', '85% coupling score'],
  },
  {
    id: 'r4', title: 'Implement API Gateway Pattern',
    recommendation: 'Add an API Gateway to manage cross-cutting concerns like authentication, rate limiting, and request routing.',
    businessValue: 'Centralized security policy reduces compliance risk by 40%',
    technicalImpact: 'Low complexity, standard AWS API Gateway implementation',
    confidence: 85, priority: 'medium', category: 'security',
    effort: '2-3 weeks', impact: 'medium',
    evidence: ['No centralized auth', 'Rate limiting missing', 'Standard pattern'],
  },
  {
    id: 'r5', title: 'Migrate to Event-Driven Architecture',
    recommendation: 'Replace synchronous REST calls between services with SQS/SNS messaging for better resilience and scalability.',
    businessValue: 'Improves system availability from 99.5% to 99.95% SLA',
    technicalImpact: 'Medium complexity, requires message broker setup',
    confidence: 82, priority: 'medium', category: 'reliability',
    effort: '4-6 weeks', impact: 'high',
    evidence: ['Synchronous coupling detected', 'Cascade failure risk', 'AWS-native solution available'],
  },
  {
    id: 'r6', title: 'Implement Database-per-Service Pattern',
    recommendation: 'Migrate shared database to individual schemas per service to enable independent data management.',
    businessValue: 'Enables independent scaling and reduces blast radius of data issues',
    technicalImpact: 'High complexity, requires data migration strategy',
    confidence: 78, priority: 'medium', category: 'architecture',
    effort: '6-8 weeks', impact: 'high',
    evidence: ['Shared database detected', 'Schema coupling high', 'Migration path clear'],
  },
];

export const debtItems: DebtItem[] = [
  { id: 'd1', category: 'God Classes', count: 2, severity: 'critical', recommendation: 'Decompose OrderManagementService and CustomerService into smaller, focused classes', description: 'Classes exceeding 500 LOC with high coupling', icon: 'AlertOctagon', trend: { value: 0, direction: 'neutral' } },
  { id: 'd2', category: 'Circular Dependencies', count: 3, severity: 'high', recommendation: 'Introduce event-driven patterns or shared interfaces to break cycles', description: 'Import/injection cycles between modules', icon: 'Zap', trend: { value: 1, direction: 'up' } },
  { id: 'd3', category: 'Dead Code', count: 12, severity: 'medium', recommendation: 'Remove unused classes and methods to reduce maintenance burden', description: 'Unreferenced classes and unused methods', icon: 'Trash2', trend: { value: 3, direction: 'down' } },
  { id: 'd4', category: 'Long Methods', count: 8, severity: 'medium', recommendation: 'Refactor methods exceeding 50 lines using Extract Method pattern', description: 'Methods exceeding 50 lines', icon: 'AlignLeft', trend: { value: 2, direction: 'down' } },
  { id: 'd5', category: 'Package Coupling', count: 5, severity: 'high', recommendation: 'Restructure package dependencies following dependency inversion principle', description: 'High inter-package coupling', icon: 'GitMerge', trend: { value: 0, direction: 'neutral' } },
  { id: 'd6', category: 'High Complexity', count: 7, severity: 'medium', recommendation: 'Simplify complex conditional logic using strategy or state patterns', description: 'Cyclomatic complexity > 15', icon: 'BarChart', trend: { value: 1, direction: 'down' } },
];

export const costComparison: CostBreakdownData = {
  current: {
    monthly: 12400,
    breakdown: { compute: 4800, storage: 2200, networking: 1800, operations: 2600, licensing: 1000 },
  },
  projected: {
    monthly: 8200,
    breakdown: { compute: 3200, storage: 1400, networking: 1200, operations: 1600, licensing: 800 },
  },
  savings: { monthly: 4200, annual: 50400, percentage: 33.9 },
  roi: { paybackPeriod: '8 months', breakEvenMonths: 8, totalSavings3Year: 151200 },
};

export const monthlyCostChart: ChartDataPoint[] = [
  { name: 'Jan', current: 12400, projected: 11200 },
  { name: 'Feb', current: 12400, projected: 10800 },
  { name: 'Mar', current: 12400, projected: 10200 },
  { name: 'Apr', current: 12400, projected: 9800 },
  { name: 'May', current: 12400, projected: 9400 },
  { name: 'Jun', current: 12400, projected: 9000 },
  { name: 'Jul', current: 12400, projected: 8800 },
  { name: 'Aug', current: 12400, projected: 8600 },
  { name: 'Sep', current: 12400, projected: 8400 },
  { name: 'Oct', current: 12400, projected: 8300 },
  { name: 'Nov', current: 12400, projected: 8200 },
  { name: 'Dec', current: 12400, projected: 8200 },
];

export const recentAnalyses: RecentAnalysis[] = [
  { id: 'a1', projectName: 'E-Commerce Monolith', date: '2026-07-25', status: 'completed', readiness: 34, risk: 'high', services: 9, fileName: 'ecommerce-monolith.zip' },
  { id: 'a2', projectName: 'Hospital Management', date: '2026-07-24', status: 'completed', readiness: 29, risk: 'high', services: 7, fileName: 'hospital-monolith.zip' },
  { id: 'a3', projectName: 'Banking Platform', date: '2026-07-20', status: 'completed', readiness: 67, risk: 'medium', services: 11, fileName: 'banking-platform.zip' },
  { id: 'a4', projectName: 'Insurance Core', date: '2026-07-18', status: 'in_progress', readiness: 0, risk: 'low', services: 0, fileName: 'insurance-core.zip' },
  { id: 'a5', projectName: 'CRM System', date: '2026-07-15', status: 'failed', readiness: 0, risk: 'low', services: 0, fileName: 'crm-system.zip' },
];

export const quickActions: QuickAction[] = [
  { id: 'q1', title: 'Upload New Project', description: 'Analyze a new Java monolith', icon: 'Upload', href: '/upload', color: 'blue' },
  { id: 'q2', title: 'View Jobs', description: 'Track analysis progress', icon: 'Briefcase', href: '/jobs', color: 'green' },
  { id: 'q3', title: 'Architecture Explorer', description: 'Service boundary analysis', icon: 'Network', href: '/architecture', color: 'purple' },
  { id: 'q4', title: 'Generate Report', description: 'Executive summary report', icon: 'FileText', href: '/reports', color: 'orange' },
];
