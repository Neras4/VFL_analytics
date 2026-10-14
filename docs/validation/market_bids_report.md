# Transfer Market and My Bids contract diagnostics

No market rows are imported into own roster; utility model is null. No game actions.

| Snapshot by collection order | Rows accepted | Total results | Complete | Requested sort | Applied |
|---|---:|---:|---|---|---|
| search-1 | 0 | 0 | True | strength | False |
| search-2 | 50 | 63 | False | strength | True |
| search-3 | 38 | 38 | True | price | False |

All 88 market rows accepted, 0 rejected. First search is a valid empty result. Second is page 1/2, 50 of 63; third 38 of 38. Form may be null; possible styles remain sets; specials tokenize into explicit levels, bare codes mean level 1. Filters preserve raw units (price filter units are not assumed to match askingPrice currency units).

| Bid observation UTC | Rows | Accepted | Rejected |
|---|---:|---:|---:|
| 2026-10-14T15:58:02.086Z | 0 | 0 | 0 |
| 2026-10-14T15:58:46.972Z | 1 | 1 | 0 |

Purchase limits, bidPrice, bidType=active, bidsCount and collection time survive locally. Bid price and competing bid count are checked against source observations in local diagnostics; public fixtures replace prices. No simultaneous duplicate bid is created.
