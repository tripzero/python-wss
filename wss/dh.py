
try:
	from Crypto.Hash.SHA256 import SHA256Hash as sha256
except:
	from hashlib import sha256 


try:
	from rdrand import RdRandom
	random = RdRandom()
	print("using hardware rdrand random number generation")
except:
	try:
		from Crypto.Random import random
		print("using Crypto.Random for random number generation")

	except:
		import random
		print("using random.random for random number generation")

class Shared:
	sharedPrime = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6BF12FFA06D98A0864D87602733EC86A64521F2B18177B200CBBE117577A615D6C770988C0BAD946E208E24FA074E5AB3143DB5BFCE0FD108E4B82D120A92108011A723C12A787E6D788719A10BDBA5B2699C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8DBBBC2DB04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127D5B05AA993B4EA988D8FDDC186FFB7DC90A6C08F4DF435C93402849236C3FAB4D27C7026C1D4DCB2602646DEC9751E763DBA37BDF8FF9406AD9E530EE5DB382F413001AEB06A53ED9027D831179727B0865A8918DA3EDBEBCF9B14ED44CE6CBACED4BB1BDB7F1447E6CC254B332051512BD7AF426FB8F401378CD2BF5983CA01C64B92ECF032EA15D1721D03F482D7CE6E74FEF6D55E702F46980C82B5A84031900B1C9E59E7C97FBEC7E8F323A97A7E36CC88BE0F1D45B7FF585AC54BD407B22B4154AACC8F6D7EBF48E1D814CC5ED20F8037E0A79715EEF29BE32806A1D58BB7C5DA76F550AA3D8A1FBFF0EB19CCB1A313D55CDA56C9EC2EF29632387FE8D76E3C0468043E8F663F4860EE12BF2D5B0B7474D6E694F91E6DCC4024FFFFFFFFFFFFFFFF
	sharedBase = 2

class DH:
	def __init__(self, privateKeyFile = None, prime = Shared.sharedPrime, base = Shared.sharedBase, privateKey = None):
		self.sharedPrime = prime
		self.sharedBase = base

		if not privateKey and not privateKeyFile:
			print("You must either specify a key, or a file with the key in it")
			return

		if privateKey:
			self.secret = privateKey
		else:
			try:
				with open(privateKeyFile) as pf:
					self.secret = int(pf.read())
			except:
				print("private key file is not valid")
				self.secret = self.genSecret(576)
				with open(privateKeyFile, 'w') as pf:
					pf.write(bytes(self.secret))

		self.sharedSecret = self.genSharedSecret()

	def genSecret(self, numBits):
		return random.getrandbits(numBits)

	def genSharedSecret(self):
		return pow(self.sharedBase, self.secret, self.sharedPrime)

	def genSymmetricKey(self, othersharedSecret):
		sharedsharedSecret = pow(othersharedSecret, self.secret, self.sharedPrime)
		return sharedsharedSecret

	def hashedSymmetricKey(self, othersharedSecret):
		symmtericKey = self.genSymmetricKey(othersharedSecret)
		s = sha256()
		s.update(str(symmtericKey))
		return s.digest()


if __name__=="__main__":
	from binascii import hexlify

	a = DH(prime=23, base=5, privateKey=6)
	b = DH(prime=23, base=5, privateKey=15)

	symmetricKeyA = hexlify(a.hashedSymmetricKey(b.sharedSecret))
	symmetricKeyB = hexlify(b.hashedSymmetricKey(a.sharedSecret))

	print ("{0} ==? {1}".format(symmetricKeyA, symmetricKeyB))

	if symmetricKeyB == symmetricKeyA:
		print("True")
	else:
		print("Symmetric Keys did not match")
		print("prime: ", a.sharedPrime)
		print("base: ", a.sharedBase)
		print("A sends B: ", a.sharedSecret)
		print("B sends A: ", b.sharedSecret)
		print("A's symmetric Key: ", a.genSymmetricKey(b.sharedSecret))
		print("B's symmetric Key: ", b.genSymmetricKey(a.sharedSecret))


