#include <Python.h>

#include "waitsms.h"
#include "waitsmsmod.h"

static PyObject* WaitCallback;
static PyThreadState* thread_state;

static PyObject *
waitsms_runloop(PyObject *self, PyObject *args)
{
    PyObject *temp;

	(void)self;
    
    if (!PyArg_ParseTuple(args, "O:set_callback", &temp))
        return NULL;
    
    if (!PyCallable_Check(temp)) {
    	PyErr_SetString(PyExc_TypeError, "parameter must be callable");
    	return NULL;
    }
    
    Py_XINCREF(temp);
    Py_XDECREF(WaitCallback);
    WaitCallback = temp;
    
	/* Déverrouillage de l'interpréteur Python */
	thread_state = PyEval_SaveThread();
	if (loop()) {
		/* Verrouillage de l'interpréteur Python */
		PyEval_RestoreThread(thread_state);

		PyErr_SetString(PyExc_RuntimeError, "Loop error");
		return NULL;
	}
    /* Verrouillage de l'interpréteur Python */
	PyEval_RestoreThread(thread_state);
        
    PyErr_SetObject(PyExc_KeyboardInterrupt, NULL);
    
    return NULL;
}

static PyMethodDef WaitSMSMethods[] = {
	{"runloop",  waitsms_runloop, METH_VARARGS,
	"runloop(callback)\n\n"
	"Run the SMS waiting loop."},
    {NULL, NULL, 0, NULL},
};

void runcallback(const char* tel, const char* msg) {
	PyObject *arglist;
	PyObject *result;
	
	/* Verrouillage de l'interpréteur Python */
	PyEval_RestoreThread(thread_state);
	arglist = Py_BuildValue("(ss)", tel, msg);
	assert(arglist != NULL);
	
	result = PyObject_CallObject(WaitCallback, arglist);
	Py_DECREF(arglist);
	
	if (result != NULL)
		Py_DECREF(result);
	
	/* Déverrouillage de l'interpréteur Python */
	thread_state = PyEval_SaveThread();
}

PyMODINIT_FUNC
initwaitsms(void)
{
	if (startup()) {
		PyErr_SetString(PyExc_RuntimeError, "Init failed");
	} else {
		Py_InitModule("waitsms", WaitSMSMethods);
	}
}
