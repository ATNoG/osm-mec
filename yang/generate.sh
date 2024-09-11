pip install pyang==2.6.0 pyangbind==0.8.5
export PYBINDPLUGIN=`/usr/bin/env python -c 'import pyangbind; import os; print ("{}/plugin".format(os.path.dirname(pyangbind.__file__)))'`
pyang --plugindir $PYBINDPLUGIN -f pybind -o ../oss/models/mec_app.py  mec-app-descriptor.yang && echo "oss done"
pyang --plugindir $PYBINDPLUGIN -f pybind -o ../meao/models/mec_app.py  mec-app-descriptor.yang && echo "meao done"