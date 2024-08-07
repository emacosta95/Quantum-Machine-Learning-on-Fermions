import torch
import torch.nn as nn
from typing import Dict, Optional
from tqdm import trange, tqdm
import numpy as np
from scipy import sparse, linalg
from math import factorial, sqrt
import matplotlib.pyplot as plt


# def gram_schmidt(matrix):
#     Q, R = torch.linalg.qr(matrix)
#     return Q


def gram_schmidt(V):
    """
    Perform Gram-Schmidt orthogonalization on the set of vectors V.
    
    Parameters:
        V (numpy.ndarray): A 2D numpy array where each column is a vector.
        
    Returns:
        numpy.ndarray: A 2D numpy array where each column is an orthonormal vector.
    """
    # Number of vectors
    num_vectors = V.shape[1]
    # Dimension of each vector
    dim = V.shape[0]
    
    # Initialize an empty array for the orthogonal vectors
    Q = np.zeros((dim, num_vectors))
    
    for i in range(num_vectors):
        # Start with the original vector
        q = V[:, i]
        
        # Subtract the projection of q onto each of the previously calculated orthogonal vectors
        for j in range(i):
            q = q - np.dot(Q[:, j], V[:, i]) * Q[:, j]
        
        # Normalize the resulting vector
        Q[:, i] = q / np.linalg.norm(q)
    
    return Q


class HartreeFock(nn.Module):

    def __init__(self, size: int, nspecies: int) -> None:
        super().__init__()

        self.hamiltonian = None

        self.size = nspecies * size
        self.initialize_weights(size=self.size)

        self.nspecies = nspecies

        self.kinetic_matrix = None
        self.twobody_matrix = None
        self.external_matrix = None

    def get_hamiltonian(
        self,
        twobody_interaction: Optional[Dict] = None,
        kinetic_term: Optional[np.ndarray] = None,
        external_potential: Optional[np.ndarray] = None,
    ):

        if twobody_interaction is not None:

            self.twobody_matrix = np.zeros((self.size, self.size, self.size, self.size))

            for item in twobody_interaction.items():
                (i1, i2, i3, i4), value = item
                self.twobody_matrix[i1, i2, i3, i4] = value

        if kinetic_term is not None:

            self.kinetic_matrix = kinetic_term

        if external_potential is not None:

            self.external_matrix = np.eye(self.size)
            self.external_matrix = np.einsum(
                "ij,j->ij", self.external_matrix, external_potential
            )


    def selfconsistent_computation(self, epochs=1000, eta=0.01):
        des = []
        herm_history = []
        orthogonality_history = []
        eigen_old = -1000
        tbar = tqdm(range(epochs))
        for i in tbar:

            effective_hamiltonian = 0.0

            if self.twobody_matrix is not None:

                effective_two_body_term = (1 / 8) * np.einsum(
                    "ijkl,ja,la->ik",
                    self.twobody_matrix,
                    self.weights.conjugate(),
                    self.weights,
                )
                # print('twobody matrix=',self.twobody_matrix)
                # print('effective_two_body_term=',effective_two_body_term)
                effective_hamiltonian += effective_two_body_term
            if self.kinetic_matrix is not None:
                effective_hamiltonian += self.kinetic_matrix
            if self.external_matrix is not None:
                effective_hamiltonian += self.external_matrix

            ishermcheck = np.average(
                np.abs(
                    effective_hamiltonian
                    - np.einsum("ij->ji", effective_hamiltonian).conjugate()
                )
            )
            
            herm_history.append(ishermcheck)
            if not (np.isclose(0, ishermcheck)):
                print("effective Hamiltonian not Hermitian \n")

            eigen, new_weights = np.linalg.eigh(effective_hamiltonian)
            
            #new_weights=np.einsum('ij,ja->ia',effective_hamiltonian,self.weights) 
            new_weights=gram_schmidt(new_weights)
            #self.weights = self.weights / np.linalg.norm(self.weights, axis=0)[None, :]

            #eigen=np.einsum('ia,ij,ja->a',np.conj(self.weights),effective_hamiltonian,self.weights)
            
            #new_weights = new_weights / np.linalg.norm(new_weights, axis=0)[None, :]

            de = np.average(np.abs(eigen_old - eigen))
            eigen_old = eigen
            self.weights = self.weights * (1 - eta) + eta * new_weights

            #self.weights = gram_schmidt(self.weights)

            
            isortho = np.average(
                np.abs(
                    np.einsum("ia,ja->ij", self.weights.conj(), self.weights)
                    - np.eye(self.size)
                )
            )

            orthogonality_history.append(isortho)
            tbar.set_description(f"de={de:.15f}")
            tbar.refresh()
            des.append(eigen)

        return (
            np.asarray(des),
            np.asarray(herm_history),
            np.asarray(orthogonality_history),
        )

    def compute_energy(
        self,
    ):
        effective_hamiltonian = 0.0

        if self.twobody_matrix is not None:

            effective_two_body_term = (1 / 8) * np.einsum(
                "ijkl,ja,la->ik",
                self.twobody_matrix,
                self.weights.conjugate(),
                self.weights,
            )
            effective_hamiltonian += effective_two_body_term
        if self.kinetic_matrix is not None:
            effective_hamiltonian += self.kinetic_matrix
        if self.external_matrix is not None:
            effective_hamiltonian += self.external_matrix

        return np.einsum(
            "ia,ij,ja->",
            self.weights.conj(),
            effective_hamiltonian,
            self.weights,
        )

    def initialize_weights(self, size: int):

        # put some conditions
        # self.weights = np.random.uniform(size=(size, size))
        # self.weights = self.weights / np.linalg.norm(self.weights, axis=0)[None, :]
        self.weights = np.eye(size)

    def create_hf_psi(self, basis: np.ndarray, nparticles_a: int,nparticles_b:int):

        psi = np.zeros(basis.shape[0])
        jdx=np.append(np.arange(nparticles_a),np.arange(nparticles_b)+basis.shape[1]//2)
        jdx=list(jdx)
        print(jdx)
        matrix=np.zeros((nparticles_a+nparticles_b,nparticles_a+nparticles_b))
        for i, b in enumerate(basis):
            idx = np.nonzero(b)[0]
            matrix = self.weights[idx,:nparticles_a+nparticles_b]
            coeff = np.linalg.det(matrix)
            psi[i] = coeff

        psi = psi / np.linalg.norm(psi)

        return psi


class HartreeFockVariational(nn.Module):

    def __init__(self, size: int, nspecies: int, mu: float = 10) -> None:
        super().__init__()

        self.hamiltonian = None

        self.size = nspecies * size
        # self.initialize_weights(size=self.size)

        self.nspecies = nspecies

        self.weights = None
        self.kinetic_matrix = None
        self.twobody_matrix = None
        self.external_matrix = None

        self.mu = mu

    def get_hamiltonian(
        self,
        twobody_interaction: Optional[Dict] = None,
        kinetic_term: Optional[np.ndarray] = None,
        external_potential: Optional[np.ndarray] = None,
    ):

        if twobody_interaction is not None:

            self.twobody_matrix = torch.zeros(
                (self.size, self.size, self.size, self.size), dtype=torch.complex64
            )

            for item in twobody_interaction.items():
                (i1, i2, i3, i4), value = item
                self.twobody_matrix[i1, i2, i3, i4] = value

        if kinetic_term is not None:

            self.kinetic_matrix = kinetic_term

        if external_potential is not None:

            self.external_matrix = torch.eye(self.size, dtype=torch.complex64)
            self.external_matrix = torch.einsum(
                "ij,j->ij", self.external_matrix, external_potential
            )

    def forward(self, psi: torch.tensor):

        effective_hamiltonian = 0.0

        if self.twobody_matrix is not None:
            effective_two_body_term = (1 / 8) * torch.einsum(
                "ijkl,ja,la->ik",
                self.twobody_matrix,
                psi.conj(),
                psi,
            )
            effective_hamiltonian += effective_two_body_term
        if self.kinetic_matrix is not None:
            effective_hamiltonian += self.kinetic_matrix
        if self.external_matrix is not None:
            effective_hamiltonian += self.external_matrix

        self.effective_hamiltonian = effective_hamiltonian

        energy = torch.einsum("ia,ij,ja->", psi.conj(), effective_hamiltonian, psi)
        normalization_constrain = torch.mean(
            torch.abs(torch.eye(self.size) - torch.einsum("ia,ja->ij", psi.conj(), psi))
        )
        # print(normalization_constrain.item())

        return energy + self.mu * normalization_constrain, normalization_constrain

    def train(self, epochs=1000, eta=0.01):
        des = []
        herm_history = []
        orthogonality_history = []
        tbar = tqdm(range(epochs))

        psi = self.initialize_weights(size=self.size)

        for i in tbar:
            self.weights.requires_grad_(True)
            # self.weights = (
            #     self.weights / torch.linalg.norm(self.weights, axis=0)[None, :]
            # )
            psi = self.weights[0] + 1j * self.weights[1]
            psi = psi / torch.linalg.norm(psi, dim=0)[None, :]

            energy, norm_constrain = self.forward(psi)

            ishermcheck = torch.mean(
                torch.abs(
                    self.effective_hamiltonian
                    - torch.einsum("ij->ji", self.effective_hamiltonian).conj()
                )
            )
            herm_history.append(ishermcheck.detach().numpy())
            if not (np.isclose(0, ishermcheck.detach().numpy())):
                print("effective Hamiltonian not Hermitian \n")

            energy.backward()
            with torch.no_grad():

                grad_energy = self.weights.grad

                self.weights -= eta * (grad_energy)  # + 2 * mu * self.weights)
                self.weights.grad.zero_()

            self.eigen = torch.einsum(
                "ia,ij,ja->a", psi.conj(), self.effective_hamiltonian, psi
            )

            # self.weights = gram_schmidt(self.weights)

            isortho = torch.mean(
                torch.abs(
                    torch.einsum("ia,ja->ij", psi.conj(), psi) - torch.eye(self.size)
                )
            )

            orthogonality_history.append(isortho.clone().detach().numpy())
            tbar.set_description(
                f"energy={energy.item():.15f}, norm constrain={norm_constrain.item():.15f}"
            )
            tbar.refresh()
            des.append(self.eigen.clone().detach().numpy())

        return (
            np.asarray(des),
            np.asarray(herm_history),
            np.asarray(orthogonality_history),
        )

    def initialize_weights(self, size: int):

        # put some conditions
        # self.weights = np.random.uniform(size=(size, size))
        # self.weights = self.weights / np.linalg.norm(self.weights, axis=0)[None, :]
        self.weights = torch.cat(
            (torch.eye(size).unsqueeze(0), torch.zeros((size, size)).unsqueeze(0)),
            dim=0,
        )
        self.weights.requires_grad_(True)

        return self.weights[0] + 1j * self.weights[1]

    def compute_psi(self):
        psi = self.weights[0] + 1j * self.weights[1]
        psi = psi / torch.linalg.norm(psi, dim=0)[None, :]
        idx = np.argsort(self.eigen.detach().numpy())

        return psi.detach().numpy()[idx]

    def create_hf_psi(self, basis: np.ndarray, nparticles_a: int,nparticles_b:int):

        psi = np.zeros(basis.shape[0])

        orbitals = self.compute_psi()
        for i, b in enumerate(basis):
            
            jdx=np.append(np.arange(nparticles_a),np.arange(nparticles_b)+basis.shape[1]//2)
            idx = np.nonzero(b)[0]
            matrix = orbitals[idx, jdx]
            coeff = np.linalg.det(matrix)
            psi[i] = coeff

        psi = psi / np.linalg.norm(psi)

        return psi
