import numpy as np

def Kpath(path,n):
    kpath = []
    for i in range(len(path)-1):
        kp1 = np.array(path[i])
        kp2 = np.array(path[i+1])
        kp  = np.array(kp2-kp1)
        for j in range(n+1):
            kpath.append(kp1+kp*j/n)
    return kpath

kps = []
with open('KPOINTS_BS') as f:
    lines = f.readlines()
    
with open('IBZKPT') as f:
    ibzkpt = f.readlines()
    
n = int(lines[1].split()[0])-1

path = []

for i in range(4,len(lines)):
    if lines[i] != '\n':
        path.append(np.array(lines[i].split()[:3],dtype=float))


kpath = []

for i in range(0,len(path),2):
    kpath.append(Kpath([path[i],path[i+1]],n))
    
kpath = np.array(kpath)

nkbands = len(kpath)*len(kpath[0])


with open('IBZKPT') as f:
    ibzkpt = f.readlines()
    
nkibz = int(ibzkpt[1])

    
with open('KPOINTS_MBJ_BS','w') as f:
    f.write('Kpoints generated automatically by the great I.R!\n')
    f.write('{}\n'.format(nkbands+nkibz))
    f.write('Reciprocal lattice\n')
    for i in range(3,len(ibzkpt)):
        f.write(ibzkpt[i])
    for i in range(len(kpath)):
        for j in range(len(kpath[i])):
            f.write('{:.5f} {:.5f} {:.5f} {}\n'.format(kpath[i,j,0],kpath[i,j,1],kpath[i,j,2],'0.00'))
            
