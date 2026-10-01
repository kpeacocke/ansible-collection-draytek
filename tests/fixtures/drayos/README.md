# DrayOS fixture provenance

- `vigor2927lac/4.5.2.2/`: sanitised output recovered from the existing
  `vigor2927lac-support` stash, which identifies it as a live-device capture.
  Hostname, WAN addresses, DNS servers, and MAC addresses are redacted.
  Pagination markers are retained. Capture method/date is not recorded.
- `vigor2927/4.4.0/`: documentation examples from the Vigor2927 Series User's
  Guide V2.2, Part X, recovered from the earlier branch. These are not live
  captures and provide regression coverage only.

Tests against these files validate parsing, not transport or live execution.
Never commit credentials, serial numbers, public addresses, or identifying
network names in future fixtures.
