import yaml from 'js-yaml';

export interface RulesConfig {
  types: {
    [key: string]: {
      must: string[];
      hints: string[];
      exclude?: string[];  // Keywords that exclude this document type
      require_any?: string[];  // At least one of these must be present
    };
  };
  issuers: {
    canonical: string[];
    normalize: { [key: string]: string };
  };
  date_priorities: {
    [key: string]: string[];
  };
  account_patterns: string[];
}

let rulesCache: RulesConfig | null = null;

/**
 * Load rules from YAML file (at build time or runtime)
 * In production, this could be fetched or inlined
 */
export async function loadRules(): Promise<RulesConfig> {
  if (rulesCache) {
    return rulesCache;
  }
  
  // Try to load from public directory, fallback to inline rules
  try {
    if (typeof window !== 'undefined') {
      const response = await fetch('/rules.yaml');
      if (response.ok) {
        const yamlText = await response.text();
        rulesCache = yaml.load(yamlText) as RulesConfig;
        return rulesCache!;
      }
    }
  } catch (error) {
    console.warn('Failed to load rules.yaml, using inline rules', error);
  }
  
  // Fallback inline rules (always available)
  rulesCache = {
    types: {
      DividendStatement: {
        must: ['Dividend statement'],
        hints: ['Record Date', 'Payment Date', 'DRP', 'Dividend Reinvestment', 'Dividend']
      },
      DistributionStatement: {
        must: ['Distribution statement', 'Distribution Advice', 'Distribution Payment'],
        hints: ['Distribution', 'Payment date', 'Record date', 'ETF', 'Managed Fund']
      },
      BankStatement: {
        must: ['Bank Statement'],
        hints: ['BSB', 'Bank Account', 'Banking', 'Account Balance', 'Bank Transaction', 'Bank Statement'],
        exclude: ['CONFIRMATION', 'CONTRACT NOTE', 'BUY', 'SELL', 'Trade', 'Brokerage', 'Consideration', 'NAV', 'Net Asset Value', 'Fund Performance', 'Shareholder', 'CHESS', 'HIN', 'SRN', 'Portfolio', 'Holdings']
      },
      BuyContract: {
        must: ['CONFIRMATION', 'BUY CONFIRMATION', 'CONTRACT NOTE'],
        hints: ['We have bought', 'Transaction Type: BUY', 'Trade Confirmation', 'Purchase', 'Acquisition', 'Buy Order', 'Consideration', 'Brokerage', 'Trade Date', 'Settlement Date', 'Confirmation Date', 'CONFIRMATION'],
        require_any: ['BUY', 'We have bought', 'Transaction Type: BUY']
      },
      SellContract: {
        must: ['CONTRACT NOTE', 'SELL'],
        hints: ['Sale', 'Disposal']
      },
      HoldingStatement: {
        must: ['CHESS', 'Issuer Sponsored', 'SRN', 'HIN', 'NAV statement', 'NAV Statement', 'Fund Performance', 'Shareholder Value', 'Shareholder Activity'],
        hints: ['Holder Identification Number', 'Statement Date', 'Holdings', 'Portfolio', 'Net Asset Value', 'NAV per Share', 'Shareholder', 'Fund Performance', 'Opening Balance', 'Closing Balance'],
        exclude: ['CONFIRMATION', 'CONTRACT NOTE', 'BUY', 'SELL', 'Trade', 'Brokerage', 'Consideration', 'We have bought', 'We have sold']
      },
      NetAssetSummaryStatement: {
        must: ['Net Asset Summary', 'NAV Summary', 'NAV statement', 'NAV Statement', 'Net Asset Value Summary'],
        hints: ['Net Asset Value', 'NAV', 'Unit Price', 'Asset Summary', 'Asset Value', 'Unit Balance', 'Total Assets', 'Total Liabilities', 'NAV per Share', 'Fund Performance', 'Shareholder Value'],
        exclude: ['CONFIRMATION', 'CONTRACT NOTE', 'BUY', 'SELL', 'Trade', 'Brokerage', 'Consideration', 'Taxation', 'Tax Year', 'Tax Return']
      },
      TaxStatement: {
        must: ['Annual Tax Statement', 'Tax Summary', 'AMMA', 'AMIT'],
        hints: ['Tax Year', 'Assessable Income']
      },
      DistributionStatement: {
        must: ['Distribution statement', 'Distribution Advice'],
        hints: ['Distribution', 'Payment date', 'Record date']
      }
    },
    issuers: {
      canonical: [
        'Computershare',
        'Link Market Services',
        'Automic',
        'BoardRoom',
        'CommSec',
        'CMC Markets',
        'nabtrade',
        'Bell Potter',
        'Vanguard',
        'iShares',
        'BlackRock',
        'Betashares',
        'Magellan'
      ],
      normalize: {
        'Computershare Limited': 'Computershare',
        'Link Market Services Limited': 'Link Market Services',
        'CMC Markets Stockbroking': 'CMC Markets',
        'Bell Potter Securities': 'Bell Potter',
        'BlackRock Investment Management': 'BlackRock',
        'iShares by BlackRock': 'iShares'
      }
    },
    date_priorities: {
      DividendStatement: ['Payment Date', 'Record Date', 'Statement Date', 'Date'],
      DistributionStatement: ['Payment Date', 'Record Date', 'Distribution Date', 'Statement Date', 'Date'],
      BankStatement: ['Statement Date', 'Period End', 'Date'],
      BuyContract: ['Trade Date', 'Settlement Date', 'Statement Date', 'Date'],
      SellContract: ['Trade Date', 'Settlement Date', 'Statement Date', 'Date'],
      HoldingStatement: ['Statement Date', 'Date'],
      TaxStatement: ['Statement Date', 'Tax Year', 'Date']
    },
    account_patterns: [
      '(?i)(?:HIN|SRN|Account|Holder(?:\\s+ID)?)[:\\s]*([A-Z0-9-]{6,})',
      '(?i)(?:Account\\s+Number|Account\\s+No\\.?)[:\\s]*([A-Z0-9-]{6,})'
    ]
  };
  
  return rulesCache;
}

