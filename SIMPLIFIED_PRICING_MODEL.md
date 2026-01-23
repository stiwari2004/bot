# Simplified Pricing Model - LLM-Based Service Orchestration Platform

## Product Positioning

**We are**: AI-powered service orchestration platform (like Ansible, but with LLM)  
**Competition**: Red Hat Ansible Automation Platform, Ansible Tower  
**Key Differentiator**: LLM automatically generates runbooks from issue descriptions

---

## Pricing Philosophy: Keep It Simple

**One Primary Metric**: Number of managed nodes  
**Secondary Metric**: LLM token usage (included up to limit, then pay-as-you-go)

**Why Simple?**
- Easy to understand (like Ansible's node-based pricing)
- Predictable costs for customers
- Aligns with infrastructure scale
- LLM costs scale with automation needs

---

## Pricing Structure

### Trial Plan (1 Month Only)

| Parameter | Value |
|-----------|-------|
| **Duration** | 30 days (1 month) |
| **Cost** | ₹0 (Free trial) |
| **Nodes** | Up to 10 nodes |
| **LLM Tokens** | 100K tokens included |
| **Executions** | Unlimited (within node limit) |
| **After Trial** | Account suspended (read-only) until upgrade |

**Purpose**: Let customers evaluate the platform

---

### Plan 1: Starter

**Target**: Small IT teams (10-50 employees, 10-50 nodes)

| Parameter | Value |
|-----------|-------|
| **Monthly Price** | ₹6,999/month |
| **Annual Price** | ₹67,190/year (20% discount = ₹83,988/year) |
| **Nodes Included** | 25 nodes |
| **LLM Tokens Included** | 300K tokens/month |
| **Executions** | Unlimited (within node limit) |
| **Overage - Nodes** | ₹200/node/month beyond 25 |
| **Overage - LLM** | ₹1.00/1K tokens beyond 300K |

**Target Customer**: Small businesses, startups

**Comparison to Ansible**:
- Ansible Tower: ~₹4-8 lakhs/year for similar scale
- Our price: ₹67K-84K/year
- **60-80% cheaper** + AI features

---

### Plan 2: Professional

**Target**: Mid-market companies (50-500 employees, 50-200 nodes)

| Parameter | Value |
|-----------|-------|
| **Monthly Price** | ₹16,999/month |
| **Annual Price** | ₹1,63,190/year (20% discount = ₹2,03,988/year) |
| **Nodes Included** | 100 nodes |
| **LLM Tokens Included** | 1.5M tokens/month |
| **Executions** | Unlimited (within node limit) |
| **Overage - Nodes** | ₹150/node/month beyond 100 |
| **Overage - LLM** | ₹0.80/1K tokens beyond 1.5M |

**Target Customer**: Growing companies, mid-market

**Comparison to Ansible**:
- Ansible Tower: ~₹8-15 lakhs/year for 100 nodes
- Our price: ₹1.6L-2L/year
- **75-80% cheaper** + AI features

---

### Plan 3: Enterprise

**Target**: Large enterprises (500+ employees, 200+ nodes)

| Parameter | Value |
|-----------|-------|
| **Monthly Price** | Custom (starts at ₹34,999/month) |
| **Annual Price** | Custom (typically 25% discount) |
| **Nodes Included** | Custom (200+ nodes) |
| **LLM Tokens Included** | Custom (5M+ tokens) |
| **Executions** | Unlimited |
| **Overage** | Negotiated rates |
| **Features** | All + white-labeling, on-premise, SLA, dedicated support |

**Target Customer**: Large enterprises

---

## Cost Analysis & Margins

### Your Costs (Monthly per Customer)

**Infrastructure**:
- Hosting (DB, Redis, App): ₹500-2,000/month
- Support: ₹500-2,000/month

**LLM Costs** (Critical):
- Gemini: ~₹0.20-0.50 per 1K tokens (your cost)
- Perplexity: ~₹0.30-0.60 per 1K tokens (your cost)
- Average: ~₹0.40 per 1K tokens

**Starter Plan Analysis** (25 nodes, 300K tokens):
- Revenue: ₹6,999/month
- Infrastructure: ₹1,000-2,000/month
- LLM costs: 300K tokens × ₹0.40 = ₹1,200/month
- Support: ₹500-1,000/month
- **Total Costs**: ₹2,700-4,200/month
- **Margin**: ₹2,800-4,300/month (40-60%)

**Professional Plan Analysis** (100 nodes, 1.5M tokens):
- Revenue: ₹16,999/month
- Infrastructure: ₹1,500-3,000/month
- LLM costs: 1.5M tokens × ₹0.40 = ₹6,000/month
- Support: ₹1,000-2,000/month
- **Total Costs**: ₹8,500-11,000/month
- **Margin**: ₹6,000-8,500/month (35-50%)

**Key Insight**: LLM costs are significant. Need to:
1. **Optimize LLM usage** (caching, efficient prompts)
2. **Charge fair overage** (2-2.5x your cost = ₹1.00/1K tokens)
3. **Volume discounts** (better LLM rates at scale)

---

## Pricing Comparison: Ansible vs Our Platform

| Feature | Ansible (Open Source) | Ansible Tower | Our Platform |
|---------|---------------------|--------------|--------------|
| **Cost** | Free | $5,000-10,000/year | ₹6,999-16,999/month |
| **Cost (INR/year)** | ₹0 | ₹4-8 lakhs | ₹67K-2L |
| **Nodes** | Unlimited | Per-node pricing | 25-100+ included |
| **AI/LLM** | ❌ No | ❌ No | ✅ Yes |
| **Playbook Writing** | Manual | Manual | ✅ Automatic |
| **Support** | Community | Red Hat | ✅ Included |
| **UI** | CLI/Basic | Tower UI | ✅ Modern |
| **India Pricing** | N/A | High | ✅ Competitive |

**Value Proposition**:
- **60-80% cheaper** than Ansible Tower
- **AI-powered** (no manual playbook writing)
- **Faster ROI** (immediate value vs. months of playbook development)

---

## Recommended Pricing Parameters

### Base Plans (INR)

| Plan | Monthly | Annual | Nodes | LLM Tokens |
|------|---------|--------|-------|-------------|
| **Trial** | ₹0 | ₹0 | 10 | 100K |
| **Starter** | ₹6,999 | ₹67,190 | 25 | 300K |
| **Professional** | ₹16,999 | ₹1,63,190 | 100 | 1.5M |
| **Enterprise** | Custom | Custom | Custom | Custom |

### Overage Rates (INR)

| Plan | Node Overage | LLM Token Overage |
|------|--------------|-------------------|
| **Starter** | ₹200/node/month | ₹1.00/1K tokens |
| **Professional** | ₹150/node/month | ₹0.80/1K tokens |
| **Enterprise** | Negotiated | Negotiated |

---

## Implementation Questions

Before implementing, need to confirm:

1. **What counts as a "node"?**
   - Server/VM?
   - Container?
   - Network device?
   - All of the above?

2. **Your actual LLM costs?**
   - Gemini: ₹? per 1K tokens
   - Perplexity: ₹? per 1K tokens
   - Average: ₹? per 1K tokens

3. **Target margin?**
   - 40-50% acceptable?
   - Or need 60%+?

4. **Trial expiration?**
   - Auto-suspend?
   - Grace period?
   - Read-only mode?

---

## Next Steps

1. **Confirm parameters** above
2. **Update codebase** with simplified pricing
3. **Remove complex seat/node/ticket combinations**
4. **Implement node-based + LLM token model**
5. **Add 1-month trial logic**

**Ready to proceed?** Share:
- Node definition (what counts as a node)
- Your actual LLM costs per 1K tokens
- Target margin percentage
- Any other constraints

Then I'll update the codebase!
