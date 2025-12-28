# %%
import numpy as np
# %%
# Make a synthetic sinusoidal curve
t = np.arange(24)

A = 1.0
mu = 1.0   # mean equals amplitude

x = mu + A * np.sin(2 * np.pi * t / 24)

mean_x = x.mean()
fft = np.fft.fft(x)
harmonic_amplitude = 2 * np.abs(fft[1]) / len(x)

rel_map = harmonic_amplitude / mean_x
rel_map
# %%
# Dirac delta
N = 24
rain = np.zeros(N)

# All rain in one hour (e.g., 17 LT)
rain[17] = 1.0
mean_rain = rain.mean()

fft = np.fft.fft(rain)
harmonic_amplitude = 2 * np.abs(fft[1]) / N

ratio = harmonic_amplitude / mean_rain

mean_rain, harmonic_amplitude, ratio

# %%
