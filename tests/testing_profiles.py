import tm_solarshift.utils.profiles as profiles
import tm_solarshift.utils.trnsys as trnsys

Sim = trnsys.Simulation()
Profiles = profiles.new_profile(Sim)
print(Profiles.head())
