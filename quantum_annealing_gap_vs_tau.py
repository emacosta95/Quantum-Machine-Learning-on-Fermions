from collections import Counter
from src.hamiltonian_utils import get_twobody_nuclearshell_model,FermiHubbardHamiltonian,SingleParticleState
import numpy as np
import torch
from typing import Dict
from src.qml_models import AdaptVQEFermiHubbard
from src.qml_utils.train import Fit
from src.qml_utils.utils import configuration
from scipy.sparse.linalg import eigsh,expm_multiply
from tqdm import trange
import matplotlib.pyplot as plt
import scipy

def plot_spectrum(eigenvalues):
    """
    Plot the vertical spectrum of a Hamiltonian, showing the eigenvalues as horizontal lines 
    and indicating their degeneracy.

    Parameters:
    eigenvalues (array-like): Array of eigenvalues of the Hamiltonian.
    """
    # Count the degeneracy of each eigenvalue
    degeneracy = Counter(eigenvalues)

    # Prepare data for plotting
    unique_eigenvalues = list(degeneracy.keys())
    degeneracies = list(degeneracy.values())

    # Plot the spectrum
    plt.figure(figsize=(6, 10))
    for i, (eig, deg) in enumerate(zip(unique_eigenvalues, degeneracies)):
        plt.hlines(eig, i - 0.2 * deg, i + 0.2 * deg, colors='b', linewidth=5)
        plt.text(i, eig, f'{deg}', horizontalalignment='center', verticalalignment='bottom', fontsize=24, color='r')

    # Make the plot fancy
    plt.title('Spectrum of the Hamiltonian', fontsize=16)
    plt.ylabel('Eigenvalue', fontsize=14)
    plt.xlabel('Index (degeneracy indicated by text)', fontsize=14)
    plt.xticks(range(len(unique_eigenvalues)), ['']*len(unique_eigenvalues))  # Remove x-axis ticks
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()

    # Show the plot
    plt.show()

name='heavy'

if name=='usdb':
    file_name='data/usdb.nat'
elif name=='cki':
    file_name='data/cki'
elif name=='heavy':
    file_name='data/usdb.nat'

SPS=SingleParticleState(file_name=file_name)
energies=SPS.energies

size_a=energies.shape[0]//2
size_b=size_a

####

if name=='usdb':
    nparts=[(2,0),(4,0),(6,0),(2,2)]
    labels=['O18','O20','O22','Ne20']
elif name=='cki':
    nparts=[(2,2),(2,4),(4,4),(2,6),(3,1),(3,3),(5,1),(5,3)]
    labels=[r'Be8',r'Be10',r'C12',r'Be12',r'Li8',r'B10',r'B6',r'B12']
elif name=='heavy':
    #labels=['Ne22','Mg24','Si28']
    #nparts=[(4,2),(4,4),(6,6)]
    
    nparts=[(6,10),(6,2),(6,4),(6,8),]
    labels=[r'Ar32',r'Ne24',r'Mg26',r'Si30']




npart_fidelities=[]
npart_errors=[]

if name=='cki':
    twobody_matrix,energies=get_twobody_nuclearshell_model(file_name=file_name)

    habcd=np.zeros((energies.shape[0],energies.shape[0],energies.shape[0],energies.shape[0]))
    iso_dict={-0.5:'n',0.5:'p'}
    values=np.asarray(list(twobody_matrix.values()))
    print(np.average(np.abs(values)))
    for key in twobody_matrix.keys():
        i,j,k,l=key
        habcd[i,j,k,l]=twobody_matrix[key]
        (n,_,ja,ma,_,tza)=SPS.state_encoding[i]
        (n,_,jb,mb,_,tzb)=SPS.state_encoding[j]
        (n,_,jc,mc,_,tzc)=SPS.state_encoding[k]
        (n,_,jd,md,_,tzd)=SPS.state_encoding[l]

        #print(ja,ma,iso_dict[tza]+'+'+iso_dict[tzb],jb,mb,'-->',jc,mc,iso_dict[tzc]+'+'+iso_dict[tzd],jd,md)
        #print('cross section=',twobody_matrix[key],'\n')
        


    average_unit_energy=np.average(np.abs(np.asarray(list(twobody_matrix.values()))))
total_tau=[]
total_gap=[]

for g in range(len(nparts)):
    nparticles_a=nparts[g][0]
    nparticles_b=nparts[g][1]


    # matrix_j,_=get_twobody_nuclearshell_model(file_name='data/j2.int')

    # energies=SPS.energies

    # diag_j=np.zeros(energies.shape[0])
    # diag_m=np.zeros(energies.shape[0])
    # label=[]
    # for i in range(energies.shape[0]):
    #     n,l,j,m,_,tz=SPS.state_encoding[i]
    #     label.append((j,m,tz))
    #     diag_j[i]=j*(j+1)
    #     diag_m[i]=m

    # Joperator = FermiHubbardHamiltonian(
    #     size_a=size_a,
    #     size_b=size_b,
    #     nparticles_a=nparticles_a,
    #     nparticles_b=nparticles_b,
    # )

    # Joperator.get_twobody_interaction(twobody_dict=matrix_j)
    # Joperator.get_external_potential(diag_j)
    # Joperator.get_hamiltonian()

    # Jdiagoperator=FermiHubbardHamiltonian(
    #     size_a=size_a,
    #     size_b=size_b,
    #     nparticles_a=nparticles_a,
    #     nparticles_b=nparticles_b,
    # )

    # Jdiagoperator.get_external_potential(diag_j)
    # Jdiagoperator.get_hamiltonian()


    # Moperator = FermiHubbardHamiltonian(
    #     size_a=size_a,
    #     size_b=size_b,
    #     nparticles_a=nparticles_a,
    #     nparticles_b=nparticles_b,
    # )

    # Moperator.get_external_potential(diag_m)
    # Moperator.get_hamiltonian()
    
    TargetHamiltonian=FermiHubbardHamiltonian(size_a=size_a,size_b=size_b,nparticles_a=nparticles_a,nparticles_b=nparticles_b,symmetries=[SPS.total_M_zero])
    print('size=',size_a+size_b,size_b)
    TargetHamiltonian.get_external_potential(external_potential=energies[:size_a+size_b])
    # just for the USDB heavy nuclei
    if name=='usdb' or name=='heavy':
        TargetHamiltonian.twobody_operator=scipy.sparse.load_npz(f'data/nuclear_twobody_matrix/usdb_{nparticles_a}_{nparticles_b}.npz')
    else:
        TargetHamiltonian.get_twobody_interaction(twobody_dict=twobody_matrix)
    TargetHamiltonian.get_hamiltonian()

    nlevels=1

    egs,psis=TargetHamiltonian.get_spectrum(n_states=nlevels)

    egs=egs[0]
    print(egs)
    psi0=psis[:,0]


    print('total_m=',SPS.compute_m_exp_value(psi=psi0,basis=TargetHamiltonian.basis))

    # We select the product state of the basis that minimizes the Hamiltonian
    if name=='heavy':
        min_b=np.zeros(size_a+size_b)
        if labels[g]=='Mg24':
            min_b=np.zeros(size_a+size_b)
            
            indices=[0,1,4,5,size_a,size_a+1,size_a+4,size_a+5]
            min_b[indices]=1.
            print(min_b)
            psi_index=TargetHamiltonian.encode[tuple(indices)]
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[psi_index]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base
            
        elif labels[g]=='Si28':
            
            indices=[0,1,2,3,4,5,size_a,size_a+1,size_a+2,size_a+3,size_a+4,size_a+5]
            min_b[indices]=1.
            print(min_b)
            psi_index=TargetHamiltonian.encode[tuple(indices)]
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[psi_index]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base
            
        elif labels[g]=='Ne22':
            min_b=np.zeros(size_a+size_b)
            indices=[0,1,4,5,size_a,size_a+5]
            min_b[indices]=1.
            print(min_b)
            psi_index=TargetHamiltonian.encode[tuple(indices)]
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[psi_index]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base
            
            
        if nparts[g]==(6,2):
            indices=[0,1,2,3,4,5,size_a,size_a+5]
            min_b[indices]=1.
            psi_index=TargetHamiltonian.encode[tuple(indices)]
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[psi_index]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base


    
        if nparts[g]==(6,4):
            indices=[0,1,2,3,4,5,size_a,size_a+1,size_a+4,size_a+5]
            min_b[indices]=1.
            psi_index=TargetHamiltonian.encode[tuple(indices)]
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[psi_index]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base
        
        if nparts[g]==(6,8):
            indices=[0,1,2,3,4,5,size_a,size_a+1,size_a+2,size_a+3,size_a+4,size_a+5,size_a+6,size_a+7]
            min_b[indices]=1.
            psi_index=TargetHamiltonian.encode[tuple(indices)]
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[psi_index]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base

        
        
        if nparts[g]==(6,10):
            indices=[0,1,2,3,4,5,size_a,size_a+1,size_a+2,size_a+3,size_a+4,size_a+5,size_a+6,size_a+7,size_a+8,size_a+11]
            min_b[indices]=1.
            psi_index=TargetHamiltonian.encode[tuple(indices)]
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[psi_index]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base
                
            
            
    else:
        if labels[g]=='O20':
            min_b=np.zeros(size_a+size_b)
            indices=[0,1,4,5]
            min_b[indices]=1.
            print(min_b)
            psi_index=TargetHamiltonian.encode[tuple(indices)]
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[psi_index]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base
            
        elif labels[g]==r'Li8':
            min_b=np.zeros(size_a+size_b)    
            min_b[[0,1,3,2+size_a]]=1
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[TargetHamiltonian._get_index(min_b)]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base
        elif labels[g]==r'B6':
            min_b=np.zeros(size_a+size_b)    
            min_b[[0,1,2,3,5,1+size_a]]=1
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[TargetHamiltonian._get_index(min_b)]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base
        elif labels[g]==r'B12':
            min_b=np.zeros(size_a+size_b)    
            min_b[[0,1,2,3,5,1+size_a,size_a,size_a+3]]=1
            psi_base=np.zeros(TargetHamiltonian.basis.shape[0])
            psi_base[TargetHamiltonian._get_index(min_b)]=1
            min = np.conj(psi_base) @ TargetHamiltonian.hamiltonian @ psi_base
        else:
            min = 10000
            min_b=0.
            for i, b in enumerate(TargetHamiltonian.basis):
                psi = np.zeros(TargetHamiltonian.basis.shape[0])
                psi[i] = 1.0
                value = np.conj(psi) @ TargetHamiltonian.hamiltonian @ psi
                if value < min:
                    min = value
                    psi_base = psi
                    min_b=b
                    
            
            print('min basis=',min_b,'min=',min,'\n')

    

    omega=0
    omega_b=4

    InitialHamiltonian=FermiHubbardHamiltonian(size_a=size_a,size_b=size_b,nparticles_a=nparticles_a,nparticles_b=nparticles_b,symmetries=[SPS.total_M_zero])

    kinetic_term:Dict={}
    adj_matrix=np.zeros((size_a+size_b,size_a+size_b))





                    
    external_field=np.zeros(size_a+size_b)
    rand=np.random.uniform(0,1,3)
    rand_dict={1/2:rand[0],-1/2:rand[1]}

    external_field=(min/(nparticles_a+nparticles_b))*min_b

            
        
            
        

        
        #external_field[i] = SPS.energies[i]


    InitialHamiltonian.get_external_potential(external_field)
    InitialHamiltonian.get_hamiltonian()

    nlevels=3

    es,psis=InitialHamiltonian.get_spectrum(n_states=nlevels)
    einitial=es[0]
    psi_initial=psis[:,0]
    print('total_m=',SPS.compute_m_exp_value(psi=psi_initial,basis=InitialHamiltonian.basis))

    count_tf=0
    
    tfs = np.linspace(1,40,30)#/average_unit_energy

    nsteps =10*(tfs)
    if nparts[g][0]%2!=0:
        nlevels=6
    else:
        if labels[g]=='O22':
            nlevels=10
        else:
            nlevels=4

    #gamma=1/(tf/2)
    #lambd=np.exp(-gamma*time)
    fidelities=[]
    relative_err=[]
    min_gap=10000
    for a in range(tfs.shape[0]):
        tf=tfs[a]
        nstep=int(nsteps[a])
        time = np.linspace(0.0, tf, nstep)
        psi = psi_initial
        dt=time[1]-time[0]
        lambd=1-time/tf
        for i in trange(nstep):

            time_hamiltonian = (
                InitialHamiltonian.hamiltonian * ( lambd[i])
                + TargetHamiltonian.hamiltonian * (1-lambd[i])
            ) #+lambd[i]*(1-lambd[i]) * IntermediateHamiltonian.hamiltonian
            values, psis = eigsh(time_hamiltonian, k=nlevels, which="SA")
            psi=expm_multiply(-1j*dt*time_hamiltonian,psi)

            e_ave=psi.conjugate().transpose()@ time_hamiltonian @ psi
            e_square_ave = (
                psi.conjugate().transpose() @ time_hamiltonian @ time_hamiltonian @ psi
            )

            if labels[g]=='O22' or labels[g]==r'Si30':
                gap=values[2]-values[0]
            elif labels[g]==r'C12':
                gap=values[3]-values[0]
            else:
                gap=values[1]-values[0]
                    
            if gap< min_gap:
                min_gap=gap
            
        degenerate_fidelity=0.
        count=0
        for j in range(values.shape[0]):
            if np.isclose(values[j],values[0]):
                degenerate_fidelity += (
                    psis[:, j].conjugate().transpose() @ psi[:]
                ) * np.conj(psis[:, j].conjugate().transpose() @ psi[:])
                count=count+1

        print('fidelity=',degenerate_fidelity,tf,'\n')
 
        if np.abs(degenerate_fidelity)>0.990 and count_tf==0:
            tau_min=tf
            count_tf+=1
            print('count=',count)
            print(degenerate_fidelity)
            print(labels[g])
        
            total_tau.append(tau_min)#*average_unit_energy)
            total_gap.append(min_gap)#/average_unit_energy)
            print('gap=',min_gap,'tau=',tau_min,'fidelity=',degenerate_fidelity,'nucleus=',labels[g],'\n')
            break

    count_tf=0

    
np.savez(f'data/quantum_annealing_results/gap_vs_tau_more_'+name,tau=total_tau,gap=total_gap,labels=labels)

    