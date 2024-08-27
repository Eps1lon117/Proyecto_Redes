from flask import Flask, request
from hashlib import sha256
import time
import json
import requests

# Definición de la clase Block que representa un bloque en la cadena
class Block:
    def __init__(self, index, transactions, timestamp, previous_hash):
        self.index = index  # Índice del bloque en la cadena
        self.transactions = transactions  # Lista de transacciones dentro del bloque
        self.timestamp = timestamp  # Marca de tiempo cuando se creó el bloque
        self.previous_hash = previous_hash  # Hash del bloque anterior

    # Método para calcular el hash del bloque utilizando SHA-256
    def compute_hash(self):
        # Convertir el diccionario del bloque en una cadena JSON ordenada por claves
        block_string = json.dumps(self.__dict__, sort_keys=True)
        # Devolver el hash del bloque
        return sha256(block_string.encode()).hexdigest()

# Definición de la clase Blockchain que representa la cadena de bloques
class Blockchain:

    difficulty = 2  # Nivel de dificultad para el algoritmo de prueba de trabajo

    def __init__(self):
        self.unconfirmed_transactions = []  # Transacciones que aún no se han confirmado/minado
        self.chain = []  # Lista que contendrá la cadena de bloques
        self.create_genesis_block()  # Crear el bloque génesis al iniciar la blockchain

    # Método para crear el bloque génesis, que es el primer bloque en la cadena
    def create_genesis_block(self):
        genesis_block = Block(0, [], time.time(), "0"*64)
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    # Propiedad para obtener el último bloque en la cadena
    @property
    def last_block(self):
        return self.chain[-1]

    # Método para imprimir un bloque específico de la cadena
    def print_block(self, n):
        if (len(self.chain) < n):  # Verifica si el bloque n existe en la cadena
            return
        else:
            block = self.chain[n]
            # Formatea y devuelve la información del bloque
            return 'Index: {}\n Transactions: {}\n Timestamp: {}\n PreviousHash: {}\n'.format(
                block.index, block.transactions, block.timestamp, block.previous_hash)

    # Algoritmo de prueba de trabajo para minar un bloque
    def proof_of_work(self, block):
        block.nonce = 0  # Inicializa el nonce del bloque
        computed_hash = block.compute_hash()
        # Incrementa el nonce hasta que el hash del bloque cumpla con la dificultad establecida
        while not computed_hash.startswith('0'*Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return computed_hash  # Devuelve el hash que cumple con la dificultad

    # Método para añadir un bloque a la cadena después de minarlo
    def add_block(self, block, proof):
        previous_hash = self.last_block.hash
        # Verifica que el hash del bloque anterior coincida
        if previous_hash != block.previous_hash:
            return False
        # Verifica si la prueba de trabajo es válida
        if not self.is_valid_proof(block, proof):
            return False
        block.hash = proof  # Asigna el hash al bloque y lo añade a la cadena
        self.chain.append(block)
        return True

    # Método de clase para validar la prueba de trabajo de un bloque
    @classmethod
    def is_valid_proof(self, block, block_hash):
        return (block_hash.startswith('0'*Blockchain.difficulty) and block_hash == block.compute_hash())

    # Método de clase para verificar la validez de toda la cadena
    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"
        for block in chain:
            block_hash = block.hash
            # Elimina el hash actual del bloque para recalcularlo
            delattr(block, "hash")
            # Verifica la validez de la prueba de trabajo y la continuidad de la cadena
            if not cls.is_valid_proof(block, block_hash) or previous_hash != block.previous_hash:
                result = False
                break
            block.hash, previous_hash = block_hash, block_hash
        return result

    # Método para añadir una nueva transacción a la lista de transacciones no confirmadas
    def new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

    # Método para minar un nuevo bloque con las transacciones pendientes
    def mine(self):
        if not self.unconfirmed_transactions:  # Verifica si hay transacciones pendientes
            return False
        last_block = self.last_block
        # Crea un nuevo bloque con las transacciones pendientes y el hash del último bloque
        new_block = Block(index=last_block.index + 1, transactions=self.unconfirmed_transactions, timestamp=time.time(), previous_hash=last_block.hash)
        proof = self.proof_of_work(new_block)  # Realiza la prueba de trabajo para el nuevo bloque
        self.add_block(new_block, proof)  # Añade el nuevo bloque a la cadena
        self.unconfirmed_transactions = []  # Vacía la lista de transacciones no confirmadas
        return new_block.index  # Devuelve el índice del bloque minado


# Configuración de la aplicación Flask
app = Flask(__name__)
blockchain = Blockchain()  # Crea una instancia de la cadena de bloques

# Añade transacciones y mina un bloque inicial para demostrar el funcionamiento
blockchain.new_transaction("a")
blockchain.new_transaction("b")
blockchain.mine()
len_bc = len(blockchain.chain)
print(blockchain.print_block(len_bc-1))  # Imprime el último bloque minado

blockchain.new_transaction("c")
blockchain.new_transaction("d")
blockchain.mine()
len_bc = len(blockchain.chain)
print(blockchain.print_block(len_bc-1))  # Imprime el último bloque minado


# Ruta para añadir una nueva transacción a la blockchain
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()  # Obtiene los datos de la transacción en formato JSON
    requiere_fields = ["author", "content"]  # Campos requeridos para una transacción válida
    for field in requiere_fields:
        if not tx_data.get(field):  # Verifica si falta algún campo
            return "Datos de transacción inválidos", 404
    tx_data["timestamp"] = time.time()  # Añade una marca de tiempo a la transacción
    blockchain.new_transaction(tx_data)  # Añade la transacción a la lista no confirmada
    return "Éxito", 201  # Devuelve una respuesta exitosa


# Ruta para obtener la cadena de bloques completa
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)  # Convierte cada bloque en un diccionario
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data})  # Devuelve la cadena de bloques en formato JSON


# Ruta para minar las transacciones pendientes
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()  # Intenta minar un nuevo bloque
    if not result:
        return "Nothing to mine"  # No hay transacciones para minar
    return "Block#{} is mined".format(result)  # Devuelve el índice del bloque minado


# Ruta para obtener las transacciones pendientes
@app.route('/pending_tx', methods=['POST'])
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)  # Devuelve las transacciones no confirmadas en formato JSON

# Inicia la aplicación Flask en el puerto 8000
app.run(port=8000)
