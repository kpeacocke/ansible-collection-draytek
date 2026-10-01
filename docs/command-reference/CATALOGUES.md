# Device evidence catalogues

These are documentation evidence, not implemented device support. Keep each model and firmware boundary separate.

| Device | Evidence | Guide / firmware | Records |
| --- | --- | --- | --- |
| Vigor2927 | [CLI](draytek-vigor2927-telnet.yaml) / [README](README.md) | User Guide V2.2 / documentation examples | 373 |
| VigorAP 1060C | [Management](draytek-vigorap-1060c-management.yaml) / [README](README-vigorap-1060c.md) | 1.4 / V1.4.9 | 46 |
| VigorAP 918R | [Management](draytek-vigorap-918r-management.yaml) / [README](README-vigorap-918r.md) | 1.6 / V1.4.6 | 70 |
| VigorSwitch P2100/G2100 | [CLI](draytek-vigorswitch-p2100-g2100-telnet.yaml) / [README](README-vigorswitch-p2100-g2100.md) | 1.3 / V2.8.3 | 83 |
| VigorSwitch G1080 | [Management](draytek-vigorswitch-g1080-management.yaml) / [README](README-vigorswitch-g1080.md) | 1.0 / V1.04.04 | 17 |

The four AP/switch catalogues have device-specific Copilot instruction files in
`../../.github/instructions/`. Generated validation reports and ZIP packages
were deliberately removed after installation; the installed YAML, README and
instruction files are the durable source set. The 1060C and P2100/G2100 YAML
catalogues were imported unchanged; their original validation claims are not a
fresh source-manual audit.

The supplied [918R manual](https://github.com/kpeacocke/ansible-collection-draytek/blob/main/docs/command-reference/sources/DrayTek_UG_VigorAP%20918R_V1.6.pdf) matches the existing catalogue source hash. The [G1080 manual](https://github.com/kpeacocke/ansible-collection-draytek/blob/main/docs/command-reference/sources/DrayTek_UG_VigorSwitch%20G1080_V1.0.pdf) was used to create its new catalogue. Source PDFs remain in Git; the Galaxy artifact includes the catalogues but excludes those PDFs.

The Vigor2927 CLI catalogue is newly installed evidence in this PR. The four
AP/switch families remain evidence-only until their transports and device
behaviour are validated. See the [support matrix](../supported_devices.md)
for the independently validated Vigor2927Lac facts support.
