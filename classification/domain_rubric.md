# Outlet-type rubric (domain classification)

Classify each news domain into exactly one outlet type, based on the domain name
and the sample headlines it published. Judge the outlet's primary audience, not
the story's topic.

- **local** — subnational audience in any country: local/regional TV or radio
  stations (incl. network affiliates, e.g. wral.com, abc15.com), city or county
  newspapers, metro alt-weeklies, community news sites (e.g. patch.com,
  insidenova.com, potomaclocal.com), state/province-level outlets.
- **national** — national or international general-interest news, incl. major
  business/financial press with a general audience (cnbc.com, forbes.com,
  reuters.com, theguardian.com, economictimes.indiatimes.com). A national outlet
  of any country counts as national, not local.
- **trade** — industry/professional press: datacenter, tech, telecom, energy,
  construction, IT trade publications (datacenterdynamics.com, theregister.com,
  networkworld.com, crn.com, developingtelecoms.com).
- **wire_pr** — newswires, press-release distribution and syndication, and
  market-data/press-release aggregators (prnewswire.com, globenewswire.com,
  businesswire.com, openpr.com, marketscreener.com, finanznachrichten.de,
  markets.financialcontent.com).
- **other** — government/military sites, company blogs, consumer deal/review
  sites without a news desk, or genuinely unidentifiable domains.

Edge rules:
- National-network affiliates with local call signs or market numbers
  (fox9.com, cbs58.com, kagstv.com) are **local**.
- Financial-news aggregators that republish press releases or market feeds are
  **wire_pr**, even if hosted by a national brand (finance.yahoo.com).
- Country-level tech/business news sites without an industry specialty
  (it-online.co.za, itwire.com) are **trade** if IT-focused, else national.
- When the domain is ambiguous and the sample headlines don't disambiguate,
  prefer **other** over guessing local/national.
