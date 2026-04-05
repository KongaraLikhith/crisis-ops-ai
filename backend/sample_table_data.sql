-- INCIDENTS
INSERT INTO incidents (
  id, title, description, severity, status,
  assigned_to, assigned_at, resolved_by, resolved_at,
  created_at, updated_at
) VALUES
('INC-001', 'Checkout API returning 500 errors', 'Users are unable to complete payments during checkout. Spike in HTTP 500s observed after evening deployment.', 'P0', 'resolved', 'ananya.sharma@company.com', '2026-04-01 18:20:00', 'ananya.sharma@company.com', '2026-04-01 19:15:00', '2026-04-01 18:05:00', '2026-04-01 19:15:00'),

('INC-002', 'Login failures for Android users', 'Android app users report repeated login failures after app update rollout.', 'P1', 'resolved', 'rohit.verma@company.com', '2026-04-01 09:10:00', 'rohit.verma@company.com', '2026-04-01 10:05:00', '2026-04-01 08:52:00', '2026-04-01 10:05:00'),

('INC-003', 'Order confirmation emails delayed', 'Transactional email service is delayed; customers are not receiving order confirmation emails on time.', 'P2', 'resolved', 'isha.kapoor@company.com', '2026-04-01 12:40:00', 'isha.kapoor@company.com', '2026-04-01 14:10:00', '2026-04-01 12:22:00', '2026-04-01 14:10:00'),

('INC-004', 'Inventory sync mismatch across warehouses', 'Stock counts are inconsistent between ERP sync and storefront inventory.', 'P1', 'resolved', 'vivek.nair@company.com', '2026-04-01 07:45:00', 'vivek.nair@company.com', '2026-04-01 11:20:00', '2026-04-01 07:30:00', '2026-04-01 11:20:00'),

('INC-005', 'Dashboard page load latency above 12 seconds', 'Internal analytics dashboard is loading extremely slowly for operations team.', 'P2', 'resolved', 'priya.singh@company.com', '2026-04-02 10:25:00', 'priya.singh@company.com', '2026-04-02 12:05:00', '2026-04-02 10:12:00', '2026-04-02 12:05:00'),

('INC-006', 'Webhook delivery failures to merchant systems', 'Outbound order webhooks are failing for several merchant integrations.', 'P1', 'resolved', 'arjun.mehra@company.com', '2026-04-02 15:00:00', 'arjun.mehra@company.com', '2026-04-02 17:35:00', '2026-04-02 14:41:00', '2026-04-02 17:35:00'),

('INC-007', 'Redis cache memory saturation causing timeouts', 'API timeouts increased significantly due to cache memory pressure on primary Redis node.', 'P0', 'resolved', 'sneha.iyer@company.com', '2026-04-02 19:15:00', 'sneha.iyer@company.com', '2026-04-02 20:05:00', '2026-04-02 19:02:00', '2026-04-02 20:05:00'),

('INC-008', 'Search results returning stale product data', 'Users are seeing outdated prices and availability in search results.', 'P1', 'resolved', 'karan.gupta@company.com', '2026-04-03 08:20:00', 'karan.gupta@company.com', '2026-04-03 10:00:00', '2026-04-03 08:03:00', '2026-04-03 10:00:00'),

('INC-009', 'KYC document uploads failing', 'Customers are unable to upload KYC verification documents from web and mobile.', 'P0', 'resolved', 'megha.rana@company.com', '2026-04-03 11:05:00', 'megha.rana@company.com', '2026-04-03 12:18:00', '2026-04-03 10:52:00', '2026-04-03 12:18:00'),

('INC-010', 'Scheduled settlement jobs not running', 'Daily merchant settlement batch did not execute overnight.', 'P0', 'resolved', 'aman.joshi@company.com', '2026-04-03 06:45:00', 'aman.joshi@company.com', '2026-04-03 08:35:00', '2026-04-03 06:30:00', '2026-04-03 08:35:00'),

('INC-011', 'Duplicate orders created on retry flow', 'A subset of customers were charged once but two orders were created after payment retry.', 'P0', 'resolved', 'nidhi.batra@company.com', '2026-04-03 16:05:00', 'nidhi.batra@company.com', '2026-04-03 18:10:00', '2026-04-03 15:48:00', '2026-04-03 18:10:00'),

('INC-012', 'Image CDN serving broken product thumbnails', 'Product listing pages show broken or missing thumbnails for many SKUs.', 'P1', 'resolved', 'yash.malhotra@company.com', '2026-04-03 13:35:00', 'yash.malhotra@company.com', '2026-04-03 15:05:00', '2026-04-03 13:18:00', '2026-04-03 15:05:00'),

('INC-013', 'Payment success page not loading after UPI completion', 'Customers complete UPI payment but are stuck on spinner instead of success page.', 'P0', 'resolved', 'riya.khanna@company.com', '2026-04-04 09:30:00', 'riya.khanna@company.com', '2026-04-04 10:40:00', '2026-04-04 09:12:00', '2026-04-04 10:40:00'),

('INC-014', 'Rate limiter blocking legitimate API traffic', 'Several enterprise clients report 429 responses despite staying within contracted limits.', 'P1', 'resolved', 'aditya.paul@company.com', '2026-04-04 11:20:00', 'aditya.paul@company.com', '2026-04-04 13:10:00', '2026-04-04 11:03:00', '2026-04-04 13:10:00'),

('INC-015', 'Customer support chat widget unavailable', 'Support chat widget is not loading on checkout and help pages.', 'P2', 'resolved', 'neha.sethi@company.com', '2026-04-04 14:05:00', 'neha.sethi@company.com', '2026-04-04 15:25:00', '2026-04-04 13:52:00', '2026-04-04 15:25:00'),

('INC-016', 'Background worker queue backlog increasing rapidly', 'Fulfillment and notification jobs are piling up in worker queues.', 'P1', 'resolved', 'saurabh.tandon@company.com', '2026-04-04 18:40:00', 'saurabh.tandon@company.com', '2026-04-04 21:00:00', '2026-04-04 18:18:00', '2026-04-04 21:00:00'),

('INC-017', 'Mobile app crash on cart page', 'iOS app crashes for some users when opening cart containing bundled products.', 'P1', 'resolved', 'tanvi.arora@company.com', '2026-04-05 10:15:00', 'tanvi.arora@company.com', '2026-04-05 12:00:00', '2026-04-05 09:58:00', '2026-04-05 12:00:00'),

('INC-018', 'Tax calculation mismatch for international orders', 'International customers are seeing incorrect tax amounts at checkout.', 'P1', 'resolved', 'harsh.vashisht@company.com', '2026-04-05 07:55:00', 'harsh.vashisht@company.com', '2026-04-05 11:10:00', '2026-04-05 07:40:00', '2026-04-05 11:10:00'),

('INC-019', 'BI reports missing previous day sales data', 'Finance and BI dashboards are missing complete sales data for the previous day.', 'P2', 'resolved', 'diksha.agarwal@company.com', '2026-04-05 08:45:00', 'diksha.agarwal@company.com', '2026-04-05 10:25:00', '2026-04-05 08:20:00', '2026-04-05 10:25:00'),

('INC-020', 'Password reset emails not being delivered', 'Users requesting password resets are not receiving reset links.', 'P1', 'resolved', 'rahul.soni@company.com', '2026-04-05 17:10:00', 'rahul.soni@company.com', '2026-04-05 18:40:00', '2026-04-05 16:52:00', '2026-04-05 18:40:00');

-- INCIDENT LOGS
INSERT INTO incident_logs (incident_id, agent, action, detail, created_at) VALUES
-- INC-001
('INC-001', 'CommanderAgent', 'severity_assigned', 'Marked incident as P0 based on payment failure rate and checkout impact.', '2026-04-01 18:07:00'),
('INC-001', 'TriageAgent', 'root_cause_hypothesis', 'Recent deployment likely introduced invalid DB credential reference for checkout service.', '2026-04-01 18:10:00'),
('INC-001', 'CommsAgent', 'slack_update_sent', 'Sent customer-impact update to #incident-war-room and #support-ops.', '2026-04-01 18:14:00'),
('INC-001', 'HumanEngineer', 'resolution_applied', 'Rolled back deployment and restored valid secret mapping in checkout service.', '2026-04-01 19:02:00'),

-- INC-002
('INC-002', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to elevated mobile login failures.', '2026-04-01 08:55:00'),
('INC-002', 'TriageAgent', 'root_cause_hypothesis', 'Android app build is sending malformed auth token after refresh flow.', '2026-04-01 09:00:00'),
('INC-002', 'CommsAgent', 'slack_update_sent', 'Notified mobile engineering and customer support teams.', '2026-04-01 09:05:00'),
('INC-002', 'HumanEngineer', 'resolution_applied', 'Disabled faulty app config remotely and restored previous auth token formatter.', '2026-04-01 09:52:00'),

-- INC-003
('INC-003', 'CommanderAgent', 'severity_assigned', 'Marked incident as P2 due to delayed but non-blocking transactional email flow.', '2026-04-01 12:24:00'),
('INC-003', 'TriageAgent', 'root_cause_hypothesis', 'Email queue backlog caused by third-party SMTP throttling.', '2026-04-01 12:29:00'),
('INC-003', 'CommsAgent', 'slack_update_sent', 'Posted internal update to support team regarding delayed confirmations.', '2026-04-01 12:33:00'),
('INC-003', 'HumanEngineer', 'resolution_applied', 'Switched to backup email provider and replayed queued jobs.', '2026-04-01 13:58:00'),

-- INC-004
('INC-004', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to oversell risk from inventory inconsistency.', '2026-04-01 07:32:00'),
('INC-004', 'TriageAgent', 'root_cause_hypothesis', 'Warehouse sync job skipped one region after schema mismatch in ERP payload.', '2026-04-01 07:40:00'),
('INC-004', 'CommsAgent', 'slack_update_sent', 'Shared ops advisory to merchandising and fulfillment channels.', '2026-04-01 07:50:00'),
('INC-004', 'HumanEngineer', 'resolution_applied', 'Patched transformer, re-ran failed sync, and reconciled inventory deltas.', '2026-04-01 10:58:00'),

-- INC-005
('INC-005', 'CommanderAgent', 'severity_assigned', 'Marked incident as P2 due to internal dashboard latency degradation.', '2026-04-02 10:14:00'),
('INC-005', 'TriageAgent', 'root_cause_hypothesis', 'Recent analytics query change triggered full table scan on reporting DB.', '2026-04-02 10:19:00'),
('INC-005', 'CommsAgent', 'slack_update_sent', 'Updated internal ops stakeholders about degraded dashboard performance.', '2026-04-02 10:23:00'),
('INC-005', 'HumanEngineer', 'resolution_applied', 'Added missing index and reverted expensive aggregation query path.', '2026-04-02 11:50:00'),

-- INC-006
('INC-006', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to failed downstream merchant notifications.', '2026-04-02 14:45:00'),
('INC-006', 'TriageAgent', 'root_cause_hypothesis', 'Webhook signing certificate rotation likely broke signature verification.', '2026-04-02 14:52:00'),
('INC-006', 'CommsAgent', 'slack_update_sent', 'Shared merchant integration impact note with partnerships team.', '2026-04-02 14:58:00'),
('INC-006', 'HumanEngineer', 'resolution_applied', 'Rolled back certificate config and replayed failed webhook deliveries.', '2026-04-02 17:10:00'),

-- INC-007
('INC-007', 'CommanderAgent', 'severity_assigned', 'Marked incident as P0 due to broad API timeout impact.', '2026-04-02 19:04:00'),
('INC-007', 'TriageAgent', 'root_cause_hypothesis', 'Redis primary exhausted memory due to unbounded session key growth.', '2026-04-02 19:08:00'),
('INC-007', 'CommsAgent', 'slack_update_sent', 'Sent urgent platform degradation update to incident channel.', '2026-04-02 19:11:00'),
('INC-007', 'HumanEngineer', 'resolution_applied', 'Evicted stale keys, increased maxmemory headroom, and patched TTL bug.', '2026-04-02 19:52:00'),

-- INC-008
('INC-008', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to stale pricing and availability in search.', '2026-04-03 08:05:00'),
('INC-008', 'TriageAgent', 'root_cause_hypothesis', 'Search index refresh pipeline stopped consuming product update events.', '2026-04-03 08:10:00'),
('INC-008', 'CommsAgent', 'slack_update_sent', 'Updated catalog and growth teams about search freshness issue.', '2026-04-03 08:15:00'),
('INC-008', 'HumanEngineer', 'resolution_applied', 'Restarted consumer, reprocessed event backlog, and validated index freshness.', '2026-04-03 09:42:00'),

-- INC-009
('INC-009', 'CommanderAgent', 'severity_assigned', 'Marked incident as P0 due to onboarding and compliance flow outage.', '2026-04-03 10:54:00'),
('INC-009', 'TriageAgent', 'root_cause_hypothesis', 'Object storage upload policy expired unexpectedly for KYC bucket.', '2026-04-03 10:58:00'),
('INC-009', 'CommsAgent', 'slack_update_sent', 'Notified risk, compliance, and support teams of upload outage.', '2026-04-03 11:02:00'),
('INC-009', 'HumanEngineer', 'resolution_applied', 'Regenerated signed upload policy and redeployed document upload config.', '2026-04-03 12:00:00'),

-- INC-010
('INC-010', 'CommanderAgent', 'severity_assigned', 'Marked incident as P0 due to missed merchant settlements.', '2026-04-03 06:32:00'),
('INC-010', 'TriageAgent', 'root_cause_hypothesis', 'Cron scheduler pod failed after node drain and did not restart correctly.', '2026-04-03 06:38:00'),
('INC-010', 'CommsAgent', 'slack_update_sent', 'Posted finance-impact update to payments and finance channels.', '2026-04-03 06:42:00'),
('INC-010', 'HumanEngineer', 'resolution_applied', 'Restarted scheduler, re-ran settlement batch, and added restart alert.', '2026-04-03 08:10:00'),

-- INC-011
('INC-011', 'CommanderAgent', 'severity_assigned', 'Marked incident as P0 due to duplicate order creation and reconciliation risk.', '2026-04-03 15:50:00'),
('INC-011', 'TriageAgent', 'root_cause_hypothesis', 'Payment retry endpoint lacks idempotency enforcement for repeated callback handling.', '2026-04-03 15:55:00'),
('INC-011', 'CommsAgent', 'slack_update_sent', 'Shared customer and finance risk update in war room.', '2026-04-03 16:00:00'),
('INC-011', 'HumanEngineer', 'resolution_applied', 'Enabled idempotency check and deduplicated impacted order records.', '2026-04-03 17:48:00'),

-- INC-012
('INC-012', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to degraded storefront media rendering.', '2026-04-03 13:20:00'),
('INC-012', 'TriageAgent', 'root_cause_hypothesis', 'CDN cache invalidation pushed broken origin path for resized thumbnails.', '2026-04-03 13:25:00'),
('INC-012', 'CommsAgent', 'slack_update_sent', 'Informed storefront and design systems teams of image issue.', '2026-04-03 13:30:00'),
('INC-012', 'HumanEngineer', 'resolution_applied', 'Restored correct origin path and purged bad CDN cache entries.', '2026-04-03 14:48:00'),

-- INC-013
('INC-013', 'CommanderAgent', 'severity_assigned', 'Marked incident as P0 due to payment completion uncertainty for UPI users.', '2026-04-04 09:14:00'),
('INC-013', 'TriageAgent', 'root_cause_hypothesis', 'Frontend polling for payment status is failing due to response contract mismatch.', '2026-04-04 09:18:00'),
('INC-013', 'CommsAgent', 'slack_update_sent', 'Sent checkout issue update to support and payments channels.', '2026-04-04 09:22:00'),
('INC-013', 'HumanEngineer', 'resolution_applied', 'Patched status API parser and deployed frontend hotfix.', '2026-04-04 10:22:00'),

-- INC-014
('INC-014', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to enterprise API request throttling.', '2026-04-04 11:05:00'),
('INC-014', 'TriageAgent', 'root_cause_hypothesis', 'Rate limiter config rollout applied incorrect tenant-level burst values.', '2026-04-04 11:10:00'),
('INC-014', 'CommsAgent', 'slack_update_sent', 'Notified API platform and customer success teams.', '2026-04-04 11:15:00'),
('INC-014', 'HumanEngineer', 'resolution_applied', 'Restored previous quota policy and invalidated stale limiter cache.', '2026-04-04 12:52:00'),

-- INC-015
('INC-015', 'CommanderAgent', 'severity_assigned', 'Marked incident as P2 due to support chat unavailability.', '2026-04-04 13:54:00'),
('INC-015', 'TriageAgent', 'root_cause_hypothesis', 'Third-party chat widget script blocked by updated content security policy.', '2026-04-04 13:58:00'),
('INC-015', 'CommsAgent', 'slack_update_sent', 'Shared fallback support guidance with customer support team.', '2026-04-04 14:02:00'),
('INC-015', 'HumanEngineer', 'resolution_applied', 'Whitelisted vendor domain in CSP and redeployed edge headers.', '2026-04-04 15:10:00'),

-- INC-016
('INC-016', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to growing async processing backlog.', '2026-04-04 18:20:00'),
('INC-016', 'TriageAgent', 'root_cause_hypothesis', 'One worker pool crashed after malformed payload repeatedly poisoned queue consumers.', '2026-04-04 18:28:00'),
('INC-016', 'CommsAgent', 'slack_update_sent', 'Updated fulfillment and notifications teams on backlog risk.', '2026-04-04 18:34:00'),
('INC-016', 'HumanEngineer', 'resolution_applied', 'Moved poison messages to DLQ and restarted worker pool with validation patch.', '2026-04-04 20:35:00'),

-- INC-017
('INC-017', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to app crash impacting cart conversion.', '2026-04-05 10:00:00'),
('INC-017', 'TriageAgent', 'root_cause_hypothesis', 'Null bundle metadata in cart response triggers unhandled rendering exception on iOS.', '2026-04-05 10:05:00'),
('INC-017', 'CommsAgent', 'slack_update_sent', 'Shared crash impact with mobile and product teams.', '2026-04-05 10:10:00'),
('INC-017', 'HumanEngineer', 'resolution_applied', 'Patched null-safe rendering and disabled broken bundle experiment.', '2026-04-05 11:42:00'),

-- INC-018
('INC-018', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to incorrect tax calculation for cross-border orders.', '2026-04-05 07:42:00'),
('INC-018', 'TriageAgent', 'root_cause_hypothesis', 'Tax provider fallback rules applied domestic VAT mapping to international regions.', '2026-04-05 07:48:00'),
('INC-018', 'CommsAgent', 'slack_update_sent', 'Notified finance, compliance, and checkout teams.', '2026-04-05 07:52:00'),
('INC-018', 'HumanEngineer', 'resolution_applied', 'Corrected region mapping table and recalculated affected pending carts.', '2026-04-05 10:45:00'),

-- INC-019
('INC-019', 'CommanderAgent', 'severity_assigned', 'Marked incident as P2 due to BI reporting data gap.', '2026-04-05 08:22:00'),
('INC-019', 'TriageAgent', 'root_cause_hypothesis', 'Nightly ETL pipeline skipped partition after schema evolution in source table.', '2026-04-05 08:28:00'),
('INC-019', 'CommsAgent', 'slack_update_sent', 'Posted finance reporting delay update to BI and finance teams.', '2026-04-05 08:35:00'),
('INC-019', 'HumanEngineer', 'resolution_applied', 'Backfilled missed partition and updated ETL schema compatibility handling.', '2026-04-05 10:05:00'),

-- INC-020
('INC-020', 'CommanderAgent', 'severity_assigned', 'Marked incident as P1 due to account recovery impact.', '2026-04-05 16:55:00'),
('INC-020', 'TriageAgent', 'root_cause_hypothesis', 'Password reset template change caused provider-side spam policy rejection.', '2026-04-05 17:00:00'),
('INC-020', 'CommsAgent', 'slack_update_sent', 'Alerted support and identity teams about password reset email issue.', '2026-04-05 17:05:00'),
('INC-020', 'HumanEngineer', 'resolution_applied', 'Reverted template change and requeued failed password reset emails.', '2026-04-05 18:20:00');

-- PAST INCIDENTS
INSERT INTO past_incidents (
  incident_id, title, description, severity, category,
  agent_root_cause, agent_resolution, agent_comms, agent_postmortem,
  human_root_cause, human_resolution,
  agent_was_correct, resolution_confidence, embedding,
  created_at, updated_at
) VALUES

('INC-001', 'Checkout API returning 500 errors', 'Users are unable to complete payments during checkout. Spike in HTTP 500s observed after evening deployment.', 'P0', 'deployment',
'Recent deployment introduced invalid DB credential reference in checkout service.',
'Rollback checkout service and restore previous secret mapping.',
'We are investigating elevated checkout failures affecting payment completion. Engineers are actively mitigating.',
'Deployment introduced a broken secret reference causing checkout service DB authentication failures and widespread payment errors.',
'Incorrect secret reference in newly deployed checkout service caused database authentication failures.',
'Rolled back checkout deployment and restored valid secret mapping. Added pre-deploy config validation.',
TRUE, 'human_verified', NULL,
'2026-04-01 19:16:00', '2026-04-01 19:16:00'),

('INC-002', 'Login failures for Android users', 'Android app users report repeated login failures after app update rollout.', 'P1', 'authentication',
'Android auth token formatter in latest app build is malformed.',
'Disable faulty mobile config and restore previous auth token behavior.',
'We are investigating Android login issues introduced after the latest app rollout.',
'Android users experienced login failures due to malformed auth refresh token handling in the latest mobile configuration.',
'Remote config pushed incompatible token formatting logic for Android refresh flow.',
'Rolled back mobile config and restored prior token format handling.',
TRUE, 'human_verified', NULL,
'2026-04-01 10:06:00', '2026-04-01 10:06:00'),

('INC-003', 'Order confirmation emails delayed', 'Transactional email service is delayed; customers are not receiving order confirmation emails on time.', 'P2', 'notifications',
'SMTP provider throttling caused queue backlog.',
'Switch to backup provider and replay delayed jobs.',
'Order confirmation emails are delayed. Orders remain successful and emails are being replayed.',
'Email confirmation delay caused by provider-side throttling and insufficient failover handling.',
'Primary email provider throttled transactional sends, causing backlog in outbound queue.',
'Failed over to backup provider and replayed queued confirmation jobs.',
TRUE, 'human_verified', NULL,
'2026-04-01 14:11:00', '2026-04-01 14:11:00'),

('INC-004', 'Inventory sync mismatch across warehouses', 'Stock counts are inconsistent between ERP sync and storefront inventory.', 'P1', 'inventory',
'Warehouse sync job skipped one region after ERP payload schema mismatch.',
'Patch payload transformer and replay failed sync batch.',
'Inventory counts may be stale for some SKUs while reconciliation is in progress.',
'Regional inventory sync skipped due to upstream ERP schema drift, causing storefront mismatch.',
'ERP payload field change broke one regional inventory transformation job.',
'Patched sync transformer, replayed failed sync, and reconciled mismatched stock counts.',
TRUE, 'human_verified', NULL,
'2026-04-01 11:21:00', '2026-04-01 11:21:00'),

('INC-005', 'Dashboard page load latency above 12 seconds', 'Internal analytics dashboard is loading extremely slowly for operations team.', 'P2', 'database_performance',
'Recent analytics query triggered full table scan on reporting DB.',
'Revert query path and add missing DB index.',
'Internal analytics dashboards are degraded due to elevated query latency.',
'Dashboard slowness caused by an unindexed reporting query introduced in recent analytics changes.',
'New aggregation path triggered full table scan due to missing index.',
'Added index and reverted expensive query path.',
TRUE, 'human_verified', NULL,
'2026-04-02 12:06:00', '2026-04-02 12:06:00'),

('INC-006', 'Webhook delivery failures to merchant systems', 'Outbound order webhooks are failing for several merchant integrations.', 'P1', 'integrations',
'Certificate rotation broke webhook signature verification.',
'Rollback signing certificate config and replay failed deliveries.',
'Some merchant webhooks are delayed or failing while delivery is being restored.',
'Webhook failures were caused by incorrect signing certificate configuration after credential rotation.',
'Rotated signing certificate did not match expected downstream verification setup.',
'Restored previous certificate config and replayed failed webhooks.',
TRUE, 'human_verified', NULL,
'2026-04-02 17:36:00', '2026-04-02 17:36:00'),

('INC-007', 'Redis cache memory saturation causing timeouts', 'API timeouts increased significantly due to cache memory pressure on primary Redis node.', 'P0', 'cache',
'Redis primary ran out of memory due to unbounded session key growth.',
'Evict stale keys, increase memory headroom, and patch TTL logic.',
'We are mitigating elevated API timeouts caused by infrastructure cache pressure.',
'Platform API degradation was caused by Redis memory saturation from session keys missing TTL expiry.',
'Session keys were written without expected TTL, causing memory exhaustion on primary Redis node.',
'Evicted stale keys, increased maxmemory headroom, and patched session TTL logic.',
TRUE, 'human_verified', NULL,
'2026-04-02 20:06:00', '2026-04-02 20:06:00'),

('INC-008', 'Search results returning stale product data', 'Users are seeing outdated prices and availability in search results.', 'P1', 'search_indexing',
'Search index consumer stopped processing product update events.',
'Restart consumer and replay indexing backlog.',
'Search freshness is degraded for some catalog updates. Reindexing is underway.',
'Stale search data was caused by halted event consumption in the product indexing pipeline.',
'Product update consumer stopped processing events after offset commit issue.',
'Restarted consumer and replayed backlog to refresh search index.',
TRUE, 'human_verified', NULL,
'2026-04-03 10:01:00', '2026-04-03 10:01:00'),

('INC-009', 'KYC document uploads failing', 'Customers are unable to upload KYC verification documents from web and mobile.', 'P0', 'storage',
'Object storage upload policy expired unexpectedly for KYC bucket.',
'Regenerate signed upload policy and redeploy upload configuration.',
'KYC document uploads are currently failing. Engineers are restoring upload access.',
'KYC upload outage was caused by expired object storage upload policy configuration.',
'Signed upload policy for compliance document storage expired and was not rotated correctly.',
'Regenerated upload policy and redeployed upload configuration.',
TRUE, 'human_verified', NULL,
'2026-04-03 12:19:00', '2026-04-03 12:19:00'),

('INC-010', 'Scheduled settlement jobs not running', 'Daily merchant settlement batch did not execute overnight.', 'P0', 'scheduler',
'Cron scheduler pod failed after node drain and did not recover.',
'Restart scheduler and re-run missed settlement batch.',
'Merchant settlements are delayed while overnight batch processing is being restored.',
'Settlement batch failed because scheduler service did not recover after infrastructure node drain.',
'Scheduler pod remained unhealthy after node maintenance and skipped overnight settlement trigger.',
'Restarted scheduler, re-ran batch, and added health-based restart alerting.',
TRUE, 'human_verified', NULL,
'2026-04-03 08:36:00', '2026-04-03 08:36:00'),

('INC-011', 'Duplicate orders created on retry flow', 'A subset of customers were charged once but two orders were created after payment retry.', 'P0', 'idempotency',
'Retry endpoint lacks idempotency enforcement for repeated callback handling.',
'Enable idempotency checks and deduplicate impacted orders.',
'We are investigating duplicate order creation affecting a subset of retry payments.',
'Duplicate orders were created because payment retry callbacks bypassed idempotency safeguards.',
'Missing idempotency enforcement in retry callback path created duplicate orders.',
'Enabled idempotency checks and repaired impacted duplicate order records.',
TRUE, 'human_verified', NULL,
'2026-04-03 18:11:00', '2026-04-03 18:11:00'),

('INC-012', 'Image CDN serving broken product thumbnails', 'Product listing pages show broken or missing thumbnails for many SKUs.', 'P1', 'cdn',
'CDN cache invalidation pushed broken origin path for resized thumbnails.',
'Restore correct origin path and purge CDN cache.',
'Some product thumbnails may appear broken while storefront media is being restored.',
'Broken product thumbnails were caused by incorrect media origin path cached at the CDN edge.',
'Resized image origin path was misconfigured during cache invalidation rollout.',
'Restored correct origin path and purged bad CDN entries.',
TRUE, 'human_verified', NULL,
'2026-04-03 15:06:00', '2026-04-03 15:06:00'),

('INC-013', 'Payment success page not loading after UPI completion', 'Customers complete UPI payment but are stuck on spinner instead of success page.', 'P0', 'frontend_backend_contract',
'Frontend polling failed due to payment status response contract mismatch.',
'Patch parser and deploy frontend hotfix.',
'We are investigating post-payment confirmation issues affecting some UPI checkouts.',
'UPI success page issue was caused by frontend parser incompatibility with updated payment status API response.',
'Payment status API returned changed field structure that frontend polling logic could not parse.',
'Patched frontend parser and restored correct success page transition.',
TRUE, 'human_verified', NULL,
'2026-04-04 10:41:00', '2026-04-04 10:41:00'),

('INC-014', 'Rate limiter blocking legitimate API traffic', 'Several enterprise clients report 429 responses despite staying within contracted limits.', 'P1', 'rate_limiting',
'Tenant burst limit config rollout applied incorrect thresholds.',
'Restore previous limiter config and invalidate stale cache.',
'Some enterprise API requests are being incorrectly rate-limited while we apply a fix.',
'Legitimate API traffic was blocked due to misapplied tenant rate limiter configuration.',
'Incorrect burst limit values were deployed for enterprise tenant rate policies.',
'Restored previous quota policy and cleared stale limiter cache.',
TRUE, 'human_verified', NULL,
'2026-04-04 13:11:00', '2026-04-04 13:11:00'),

('INC-015', 'Customer support chat widget unavailable', 'Support chat widget is not loading on checkout and help pages.', 'P2', 'frontend_security',
'Third-party widget script blocked by updated content security policy.',
'Whitelist vendor domain and redeploy CSP headers.',
'Support chat is temporarily unavailable; alternate support channels remain available.',
'Support widget outage was caused by content security policy changes blocking third-party script execution.',
'Recently updated CSP headers blocked approved chat vendor assets.',
'Whitelisted vendor domain and redeployed edge security headers.',
TRUE, 'human_verified', NULL,
'2026-04-04 15:26:00', '2026-04-04 15:26:00'),

('INC-016', 'Background worker queue backlog increasing rapidly', 'Fulfillment and notification jobs are piling up in worker queues.', 'P1', 'queue_processing',
'Malformed payload repeatedly poisoned worker consumers.',
'Move poison messages to DLQ and restart worker pool.',
'Asynchronous job processing is delayed while worker capacity is being restored.',
'Worker queue backlog was caused by poison messages crashing consumers in one processing pool.',
'Malformed payload repeatedly crashed worker consumers and blocked queue throughput.',
'Moved poison jobs to DLQ, restarted workers, and added payload validation.',
TRUE, 'human_verified', NULL,
'2026-04-04 21:01:00', '2026-04-04 21:01:00'),

('INC-017', 'Mobile app crash on cart page', 'iOS app crashes for some users when opening cart containing bundled products.', 'P1', 'mobile_crash',
'Null bundle metadata triggered unhandled iOS rendering exception.',
'Add null-safe handling and disable faulty experiment.',
'We are investigating a cart-page crash affecting some mobile users.',
'Cart page crash was caused by null bundle metadata not handled safely in the iOS rendering path.',
'Bundled product experiment returned incomplete metadata, causing cart rendering crash.',
'Patched null-safe rendering and disabled broken bundle experiment.',
TRUE, 'human_verified', NULL,
'2026-04-05 12:01:00', '2026-04-05 12:01:00'),

('INC-018', 'Tax calculation mismatch for international orders', 'International customers are seeing incorrect tax amounts at checkout.', 'P1', 'pricing_tax',
'Fallback tax rules applied domestic VAT mapping to international regions.',
'Correct region mapping and recalculate pending carts.',
'We are correcting tax calculation issues affecting some international orders.',
'Incorrect international tax values were caused by region mapping fallback applying domestic tax rules.',
'Region mapping table incorrectly routed international orders to domestic VAT logic.',
'Corrected region mapping and recalculated pending carts with proper tax rules.',
TRUE, 'human_verified', NULL,
'2026-04-05 11:11:00', '2026-04-05 11:11:00'),

('INC-019', 'BI reports missing previous day sales data', 'Finance and BI dashboards are missing complete sales data for the previous day.', 'P2', 'etl_pipeline',
'Nightly ETL skipped partition after source schema evolution.',
'Backfill missed partition and update schema compatibility handling.',
'Previous day reporting is incomplete while data backfill is in progress.',
'BI reporting gap was caused by ETL partition skip after upstream schema evolution.',
'ETL parser failed on new source schema and skipped one daily sales partition.',
'Backfilled missing partition and patched ETL schema handling.',
TRUE, 'human_verified', NULL,
'2026-04-05 10:26:00', '2026-04-05 10:26:00'),

('INC-020', 'Password reset emails not being delivered', 'Users requesting password resets are not receiving reset links.', 'P1', 'identity_notifications',
'Updated reset template triggered provider-side spam policy rejection.',
'Revert template and requeue failed reset emails.',
'Password reset emails are delayed or failing while delivery is being restored.',
'Password reset delivery failed because updated email content triggered provider policy rejection.',
'Recent password reset template revision was rejected by provider spam filters.',
'Reverted template change and requeued failed reset emails.',
TRUE, 'human_verified', NULL,
'2026-04-05 18:41:00', '2026-04-05 18:41:00');