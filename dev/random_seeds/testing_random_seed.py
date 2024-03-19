import numpy as np
from numpy.random import PCG64, SeedSequence


N_events = 5

# seed = 89936438650739816043972796915642811591
seed = SeedSequence().entropy
print(seed)
rng = np.random.default_rng(seed)

#Getting two
choice1 = rng.choice( np.arange(10), size=N_events,)
print(choice1)
choice2 = rng.choice( np.arange(10), size=N_events,)
print(choice2)
print()

#Regenerating from zero
rng = np.random.default_rng(seed)
choice1 = rng.choice( np.arange(10), size=N_events,)
print(choice1)
rng = np.random.default_rng(seed)
choice2 = rng.choice( np.arange(10), size=N_events,)
print(choice2)
choice2 = rng.choice( np.arange(10), size=N_events,)
print(choice2)
print()
pass

#Second case, including scipy
from scipy.stats import truncnorm
rng = np.random.default_rng(seed)
truncnorm.random_state = rng
truncnorm1 = truncnorm.rvs( 0, 1, loc=0.5, scale=0.2, size=N_events)
choice3 = rng.choice( np.arange(10), size=N_events)
print(truncnorm1)
print(choice3)
print()

rng = np.random.default_rng(seed)
truncnorm.random_state = rng
truncnorm1 = truncnorm.rvs( 0, 1, loc=0.5, scale=0.2, size=N_events)
choice3 = rng.choice( np.arange(10), size=N_events)
print(truncnorm1)
print(choice3)
print()
pass

rng = np.random.default_rng(seed)
choice3 = rng.choice( np.arange(10), size=N_events)
truncnorm1 = truncnorm.rvs( 0, 1, loc=0.5, scale=0.2, size=N_events)
print(truncnorm1)
print(choice3)
pass
#Exploring Generators
bg = PCG64(12345678903141592653589793)

# Creating a bit-generator from a seed

# Get the user's seed somehow, maybe through `argparse`.
# If the user did not provide a seed, it should return `None`.
def get_user_seed():
    return 1

seed = get_user_seed()
ss = SeedSequence(seed)
print('seed = {}'.format(ss.entropy))
bg = PCG64(ss)
pass

# Creating a list of generators (option 1)
# High quality initial entropy
entropy = 0x87351080e25cb0fad77a44a3be03b491
base_bitgen = PCG64(entropy)
generators = base_bitgen.spawn(12)
pass

# Creating a list of generators (option 2)
entropy = 0x87351080e25cb0fad77a44a3be03b491
sequences = [SeedSequence((entropy, worker_id)) for worker_id in range(12)]
generators = [PCG64(seq) for seq in sequences]

pass