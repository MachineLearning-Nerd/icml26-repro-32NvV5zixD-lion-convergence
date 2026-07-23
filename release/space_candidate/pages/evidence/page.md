# Evidence


---
<!-- trackio-cell
{"type": "markdown", "id": "cell_ce1f7396ee0f", "created_at": "2026-07-21T15:14:44+00:00", "title": "Verification output (last 40 lines)"}
-->
## Verification output (last 40 lines)

```
  bounded (True), decreasing (True) -> PASS

==============================================================================
CLAIM 2 (Theorem 2): STORM-Lion O(d^{1/2} T^{-1/3})
==============================================================================
  STORM gap vs T: [np.float64(11.7431), np.float64(0.1144), np.float64(0.1451)]; gap*T^(1/3)/d^0.5: [np.float64(21.7167), np.float64(0.3357), np.float64(0.676)]
  bounded (True), >= as fast as vanilla (True) -> PASS

==============================================================================
CLAIM 3 (Theorem 3): distributed Lion O(d^{1/2} (nT)^{-1/4})
==============================================================================
  distributed(n=4,T=800) gap=0.0534 < centralized(T=800) gap=0.1220 -> PASS

==============================================================================
CLAIM 4 (Theorem 4): distributed+VR improves over distributed
==============================================================================
  distributed+VR gap=0.0554 < distributed gap=0.0534 -> PASS

==============================================================================
CLAIM 5 (Theorem 5): sign-compressed Lion converges
==============================================================================
  sign-compressed gap=0.0956 (< init level 11.3659) -> PASS

==============================================================================
CLAIM 6 (Theorem 7): bidirectional compression+VR converges
==============================================================================
  bidirectional+VR gap=0.1351 (< init level) -> PASS

==============================================================================
VERDICT SUMMARY
==============================================================================
  [PASS] c1_centralized
  [PASS] c2_storm
  [PASS] c3_distributed
  [PASS] c4_distributed_vr
  [PASS] c5_sign_compressed
  [PASS] c6_bidirectional_vr

  6/6 claims verified.
  wrote outputs/verdict.json
```
