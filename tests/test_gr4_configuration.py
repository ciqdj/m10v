"""Keep the GR IV build contract aligned with shared web configuration."""
import unittest
from scripts.build_gr4_m10v_firmware import initial_state


class Gr4ConfigurationTests(unittest.TestCase):
    def configuration(self):
        slot={
            'film':33,'grain':0,'soft':0,
            'halo':{'gain':3,'spread':3,'threshold':5,'profile':2},
            'effects':{'grainSize':1,'leakGain':0,'leakPosition':0,
                       'leakSpread':4,'leakVariation':0,'filmExposure':0},
        }
        return {'slots':[slot.copy() for _ in range(5)],'stamp':0,'format':0,
                'corner':0,'color':0,'hdf':0,'filmNameStamp':False}

    def test_disabled_film_name_field_is_accepted(self):
        self.assertEqual(initial_state(self.configuration()),
                         initial_state({k:v for k,v in self.configuration().items() if k!='filmNameStamp'}))

    def test_enabled_or_invalid_film_name_field_is_rejected(self):
        for value in (True,0,None,'false'):
            config=self.configuration();config['filmNameStamp']=value
            with self.assertRaisesRegex(ValueError,'film name stamp'):
                initial_state(config)


if __name__=='__main__':unittest.main()
