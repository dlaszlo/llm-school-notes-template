"""A discontinuous function: split the domain instead of bridging its pole."""
from pathlib import Path
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out = Path(os.environ['VISUAL_OUTPUT_DIR'])
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'svg.fonttype': 'none',
                     'svg.hashsalt': 'school-notes-function-example'})
fig, ax = plt.subplots(figsize=(8, 5), layout='constrained')
for lo, hi in [(-4, -.18), (.18, 4)]:
    x = np.linspace(lo, hi, 600)
    y = 1 / x
    assert np.allclose(x * y, 1) and not np.any(x == 0)
    ax.plot(x, y, color='#17628c', linewidth=2.4)
ax.axvline(0, linestyle='--', color='#995015', linewidth=1.4, label='x = 0: not in the domain')
ax.axhline(0, color='#66717b', linewidth=.8)
ax.scatter([-2, -1, 1, 2], [-.5, -1, 1, .5], color='#17628c', zorder=3)
ax.set(xlim=(-4, 4), ylim=(-4, 4), xlabel='x', ylabel='f(x)', title='f(x) = 1/x: two separate branches')
ax.grid(alpha=.22)
ax.legend(loc='upper right', fontsize=10)
fig.savefig(out / 'figure.svg', metadata={'Date': None})
svg = out / 'figure.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
fig.savefig(out / 'figure.png', dpi=150)
plt.close(fig)
