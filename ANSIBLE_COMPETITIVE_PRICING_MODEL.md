# Ansible-Competitive Pricing Model - LLM-Based Service Orchestration

## Product Positioning

**We are**: LLM-powered service orchestration and automation platform  
**Competition**: Red Hat Ansible Automation Platform, Ansible Tower  
**Market**: India IT Operations Automation  
**Key Differentiator**: AI/LLM-powered runbook generation and execution

---

## Competitive Analysis: Ansible Pricing

### Red Hat Ansible Automation Platform
- **Standard Subscription**: ~$5,000-10,000/year (small deployments)
- **Per-node pricing**: ~$100-200/node/year
- **Enterprise**: Custom pricing (typically $15,000-50,000/year)
- **Open Source**: Free (but no enterprise features, support, or UI)

### Our Advantage
- **AI-powered**: LLM generates runbooks automatically
- **No manual playbook writing**: Describe issue, get runbook
- **Intelligent execution**: Context-aware automation
- **Modern UI**: Better than Ansible Tower

---

## Simplified Pricing Model

**Strategy**: Keep it simple - choose ONE primary metric, not multiple

### Option 1: Node-Based Pricing (Recommended)
**Primary Metric**: Number of managed infrastructure nodes

**Rationale**:
- Easy to understand (like Ansible)
- Aligns with customer infrastructure
- Predictable costs
- LLM costs scale with nodes (more nodes = more automation)

### Option 2: Execution-Based Pricing
**Primary Metric**: Number of runbook executions per month

**Rationale**:
- Pay for actual usage
- LLM costs directly tied to executions
- Fair pricing model

**Recommendation**: **Node-Based Pricing** (easier to sell, more predictable)

---

## Recommended Pricing Structure

### Trial Plan (1 Month Free)

| Parameter | Value |
|-----------|-------|
| **Duration** | 1 month (30 days) |
| **Nodes** | Up to 10 nodes |
| **Executions** | Unlimited (within node limit) |
| **LLM Tokens** | 100K tokens included |
| **Features** | Full feature access |
| **Purpose** | Customer evaluation |

**After Trial**: Must upgrade to paid plan or account is suspended (read-only mode)

---

## Paid Plans

### Plan 1: Starter (Small Teams)
**Target**: Small IT teams managing 10-50 nodes

| Parameter | Value |
|-----------|-------|
| **Monthly Cost** | ₹4,999/month |
| **Annual Cost** | ₹47,990/year (20% discount = ₹59,988/year) |
| **Nodes Included** | 25 nodes |
| **LLM Tokens/Month** | 500K tokens included |
| **Executions** | Unlimited (within node limit) |
| **Overage** | ₹200/node/month beyond 25 nodes |
| **LLM Overage** | ₹0.50/1K tokens beyond 500K |
| **Features** | All integrations, API access, basic support |

**Target Customer**: Small businesses, startups (10-50 employees)

---

### Plan 2: Professional (Mid-Market)
**Target**: Growing companies managing 50-200 nodes

| Parameter | Value |
|-----------|-------|
| **Monthly Cost** | ₹12,999/month |
| **Annual Cost** | ₹1,24,790/year (20% discount = ₹1,55,988/year) |
| **Nodes Included** | 100 nodes |
| **LLM Tokens/Month** | 2M tokens included |
| **Executions** | Unlimited (within node limit) |
| **Overage** | ₹150/node/month beyond 100 nodes |
| **LLM Overage** | ₹0.40/1K tokens beyond 2M |
| **Features** | All features, advanced RBAC, priority support, analytics |

**Target Customer**: Mid-market companies (50-500 employees)

---

### Plan 3: Enterprise (Large Organizations)
**Target**: Large enterprises managing 200+ nodes

| Parameter | Value |
|-----------|-------|
| **Monthly Cost** | Custom (starts at ₹29,999/month) |
| **Annual Cost** | Custom (typically 25% discount) |
| **Nodes Included** | Custom (200+ nodes) |
| **LLM Tokens/Month** | Custom (5M+ tokens) |
| **Executions** | Unlimited |
| **Overage** | Negotiated rates |
| **Features** | All features + white-labeling, on-premise, SLA, dedicated support |

**Target Customer**: Large enterprises (500+ employees)

---

## Pricing Comparison: Ansible vs Our Platform

| Feature | Ansible (Open Source) | Ansible Tower | Our Platform |
|---------|---------------------|--------------|--------------|
| **Cost** | Free | $5,000-10,000/year | ₹4,999-12,999/month |
| **Nodes** | Unlimited | Per-node pricing | 25-100+ included |
| **AI/LLM** | ❌ No | ❌ No | ✅ Yes - Auto-generates runbooks |
| **Playbook Writing** | Manual | Manual | ✅ Automatic from issue description |
| **Support** | Community | Red Hat Support | Included |
| **UI** | CLI/Web (basic) | Tower UI | ✅ Modern web UI |
| **India Pricing** | N/A | ~₹4-8 lakhs/year | ₹60K-1.5L/year |

**Value Proposition**: 
- **Cheaper than Ansible Tower** (especially for <100 nodes)
- **AI-powered** (no manual playbook writing)
- **Better ROI** (faster time-to-value)

---

## Cost Structure & Margins

### Your Costs Per Customer (Monthly)

**Infrastructure Costs**:
- Hosting (DB, Redis, App servers): ₹500-2,000/month
- LLM API costs (Gemini/Perplexity): 
  - ~₹2-5 per 1K tokens (your cost)
  - 500K tokens = ₹1,000-2,500/month
  - 2M tokens = ₹4,000-10,000/month
- Support: ₹500-2,000/month

**Starter Plan (25 nodes, 500K tokens)**:
- Revenue: ₹4,999/month
- Costs: ₹2,000-4,500/month
- Margin: ₹500-3,000/month (10-60%)
- **Note**: Low margin due to LLM costs

**Professional Plan (100 nodes, 2M tokens)**:
- Revenue: ₹12,999/month
- Costs: ₹5,000-14,000/month
- Margin: ₹0-8,000/month (0-60%)
- **Note**: Margin improves with scale

**Key Insight**: LLM costs are significant. Need to:
1. **Optimize LLM usage** (caching, efficient prompts)
2. **Pass through LLM costs** (charge for tokens beyond included)
3. **Volume discounts** (better LLM rates at scale)

---

## Revised Pricing (Accounting for LLM Costs)

### Starter Plan - Revised

| Parameter | Value |
|-----------|-------|
| **Monthly Cost** | ₹5,999/month |
| **Annual Cost** | ₹57,590/year (20% discount) |
| **Nodes** | 25 nodes |
| **LLM Tokens** | 300K tokens included (reduced) |
| **Overage - Nodes** | ₹200/node/month |
| **Overage - LLM** | ₹1.00/1K tokens (2x your cost) |

**Rationale**: Higher base price to cover LLM costs, but still competitive vs Ansible

### Professional Plan - Revised

| Parameter | Value |
|-----------|-------|
| **Monthly Cost** | ₹14,999/month |
| **Annual Cost** | ₹1,43,990/year (20% discount) |
| **Nodes** | 100 nodes |
| **LLM Tokens** | 1.5M tokens included |
| **Overage - Nodes** | ₹150/node/month |
| **Overage - LLM** | ₹0.80/1K tokens |

---

## Alternative: Hybrid Model (Simplified)

**Base Subscription + LLM Usage**

### Simplified Structure

| Plan | Base Price/Month | Nodes | LLM Tokens Included | LLM Overage |
|------|-----------------|-------|---------------------|-------------|
| **Trial** | ₹0 (1 month) | 10 | 100K | ₹1.00/1K |
| **Starter** | ₹5,999 | 25 | 300K | ₹1.00/1K |
| **Professional** | ₹14,999 | 100 | 1.5M | ₹0.80/1K |
| **Enterprise** | Custom | Custom | Custom | Negotiated |

**Key Points**:
- **One primary metric**: Nodes (simple to understand)
- **LLM costs included** up to limit, then pay-as-you-go
- **No complex seat/node/ticket combinations**
- **Transparent pricing**

---

## India Market Considerations

### Pricing Sensitivity
- **SMBs**: Very price-sensitive, prefer ₹5,000-8,000/month range
- **Mid-Market**: Value-focused, willing to pay ₹10,000-20,000/month
- **Enterprise**: Price less important than features/support

### Payment Preferences
- **Annual prepayment**: Preferred (20% discount)
- **Quarterly**: 10% discount
- **Monthly**: Full price
- **Payment methods**: UPI, Net Banking, Cards

### Competitive Positioning
- **vs Ansible Open Source**: We offer support + AI features
- **vs Ansible Tower**: We're 50-70% cheaper
- **vs Custom Scripts**: We're faster to implement

---

## Recommended Final Pricing

### Tier 1: Trial (1 Month)
- **Cost**: ₹0
- **Nodes**: 10
- **LLM Tokens**: 100K
- **Duration**: 30 days only

### Tier 2: Starter
- **Monthly**: ₹5,999/month
- **Annual**: ₹57,590/year (save ₹11,998)
- **Nodes**: 25 nodes
- **LLM Tokens**: 300K/month included
- **Overage**: ₹200/node, ₹1.00/1K tokens

### Tier 3: Professional
- **Monthly**: ₹14,999/month
- **Annual**: ₹1,43,990/year (save ₹35,998)
- **Nodes**: 100 nodes
- **LLM Tokens**: 1.5M/month included
- **Overage**: ₹150/node, ₹0.80/1K tokens

### Tier 4: Enterprise
- **Custom pricing**: Starts at ₹29,999/month
- **Nodes**: 200+ (custom)
- **LLM Tokens**: Custom (5M+)
- **Features**: All + white-labeling, on-premise, SLA

---

## Implementation Plan

### Phase 1: Update Pricing Model
1. Update `license_service.py` with new plans
2. Remove complex seat/node/ticket combinations
3. Focus on node-based + LLM token model
4. Add 1-month trial logic

### Phase 2: Billing Updates
1. Simplify billing calculator (nodes + LLM tokens only)
2. Add trial expiration logic
3. Implement overage billing
4. Add usage alerts (80% of limits)

### Phase 3: Pricing Page
1. Create comparison table (vs Ansible)
2. Show annual savings prominently
3. Display LLM token usage clearly
4. Add ROI calculator

---

## Key Questions to Answer

1. **What's your actual LLM cost per 1K tokens?**
   - Gemini: ~₹0.20-0.50/1K tokens?
   - Perplexity: ~₹0.30-0.60/1K tokens?
   - Need to know to set overage rates

2. **What's your target margin?**
   - 40-50% acceptable given LLM costs?
   - Or need 60%+?

3. **Trial conversion strategy?**
   - Auto-suspend after trial?
   - Grace period?
   - Downgrade to read-only?

4. **Node definition?**
   - What counts as a "node"?
   - Server? VM? Container? Network device?

---

## Next Steps

1. **Confirm LLM costs** - Need actual per-token costs
2. **Finalize node definition** - What counts as a node?
3. **Set overage rates** - Based on your LLM costs + margin
4. **Update codebase** - Implement simplified pricing
5. **Create pricing page** - Show vs Ansible comparison

**Ready to proceed?** Let me know:
- Your actual LLM costs per 1K tokens
- Target margin percentage
- Node definition (what counts as a node)
- Any other constraints

Then I'll update the codebase with the final pricing model!
