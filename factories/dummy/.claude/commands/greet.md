---
description: Runs the product's greeting and verifies the invariant marker.
run:
- python
- -c
- import sys; sys.path.insert(0, 'domain'); import greeting; assert greeting.greet()
  == 'DUMMY_OK'; print(greeting.greet())
---

# /greet — run the dummy factory's product
Run the product's greeting and confirm it returns the invariant marker DUMMY_OK.
