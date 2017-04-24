from pycoin.intbytes import byte_to_int

from ..script.VM import ScriptTools

from ... import encoding

from ...serialize import b2h

from ..exceptions import SolvingError

from .ScriptType import ScriptType


class ScriptPayToAddressWit(ScriptType):
    TEMPLATE = ScriptTools.compile("OP_0 OP_PUBKEYHASH")

    def __init__(self, version, hash160):
        assert len(version) == 1
        assert isinstance(version, bytes)
        assert len(hash160) == 20
        assert isinstance(hash160, bytes)
        version_int = byte_to_int(version[0])
        assert 0 <= version_int <= 16
        self.version = version_int
        self.hash160 = hash160
        self._address = None
        self._script = None

    @classmethod
    def from_script(cls, script):
        r = cls.match(script)
        if r:
            hash160 = r["PUBKEYHASH_LIST"][0]
            if len(hash160) == 20:
                s = cls(b'\0', hash160)
                return s
        raise ValueError("bad script")

    def script(self):
        if self._script is None:
            # create the script
            STANDARD_SCRIPT_OUT = "OP_%d %s"
            script_text = STANDARD_SCRIPT_OUT % (self.version, b2h(self.hash160))
            self._script = ScriptTools.compile(script_text)
        return self._script

    def solve(self, **kwargs):
        """
        The kwargs required depend upon the script type.
        hash160_lookup:
            dict-like structure that returns a secret exponent for a hash160
        signature_for_hash_type_f:
            function returning sign value for a given signature type
        signature_type:
            usually SIGHASH_ALL (1)
        """
        # we need a hash160 => secret_exponent lookup
        db = kwargs.get("hash160_lookup")
        if db is None:
            raise SolvingError("missing hash160_lookup parameter")
        result = db.get(self.hash160)
        if result is None:
            raise SolvingError("can't find secret exponent for %s" % self.address())
        # we got it
        script_to_hash = ScriptTools.compile(
            "OP_DUP OP_HASH160 %s OP_EQUALVERIFY OP_CHECKSIG" % b2h(self.hash160))

        signature_for_hash_type_f = kwargs.get("signature_for_hash_type_f").witness
        signature_type = kwargs.get("signature_type")

        secret_exponent, public_pair, compressed = result

        binary_signature = self._create_script_signature(
            secret_exponent, signature_for_hash_type_f, signature_type, script_to_hash)
        binary_public_pair_sec = encoding.public_pair_to_sec(public_pair, compressed=compressed)

        solution = [binary_signature, binary_public_pair_sec]
        return (b'', solution)

    def info(self, netcode=None):
        def address_f(netcode=netcode):
            from pycoin.networks import address_wit_prefix_for_netcode
            from pycoin.networks.default import get_current_netcode
            if netcode is None:
                netcode = get_current_netcode()
            address_prefix = address_wit_prefix_for_netcode(netcode)
            address = encoding.b2a_hashed_base58(address_prefix + b'\0\0' + self.hash160)
            # address = encoding.hash160_sec_to_bitcoin_address(self.hash160, address_prefix=address_prefix)
            return address
        return dict(type="pay to address", address="DEPRECATED call address_f instead",
                    address_f=address_f, hash160=self.hash160, script=self._script)

    def __repr__(self):
        return "<Script: pay to %s (segwit)>" % self.address()
