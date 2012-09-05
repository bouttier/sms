#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include <signal.h>
#include <gnokii.h>

#include <locale.h>
#include <libintl.h>

#include "waitsms.h"
#include "waitsmsmod.h"

static char *configfile = NULL;
static char *configmodel = NULL;

static struct gn_statemachine *state;
static gn_data *data;

static int cont = 1;

static void busterminate(void)
{
	if (state) {
		gn_lib_phone_close(state);
		gn_lib_phoneprofile_free(&state);
	}
	gn_lib_library_free();
}

static int businit(void)
{
	gn_error err;
	if ((err = gn_lib_phoneprofile_load_from_file(configfile, configmodel, &state)) != GN_ERR_NONE) {
		fprintf(stderr, "%s\n", gn_error_print(err));
		if (configfile)
			fprintf(stderr, "File: %s\n", configfile);
		if (configmodel)
			fprintf(stderr, "Phone section: [phone_%s]\n", configmodel);
		return 2;
	}

	/* register cleanup function */
	atexit(busterminate);

	if ((err = gn_lib_phone_open(state)) != GN_ERR_NONE) {
		fprintf(stderr, "%s\n", gn_error_print(err));
		return 2;
	}
	data = &state->sm_data;
	return 0;
}

void sigint_handler(int sig)
{
	signal(sig, SIG_IGN);
	cont = 0;
}

/* Callback appelé lors de la réception d’un SMS */
static gn_error smsslave(gn_sms* message, struct gn_statemachine* state,
	void *callback_data) {
	gn_sms message_suppr;
	gn_sms_folder folder;
	gn_sms_folder_list folderlist;
	
	const char* s = (const char*)message->user_data[0].u.text;
	const char* number = message->remote.number;
	
	gn_error error;
	
	(void)callback_data;
	
	runcallback(number, s);
		
	message_suppr.memory_type = GN_MT_IN;
	message_suppr.number = 1;
	data->sms = &message_suppr;
	data->sms_folder = &folder;
	data->sms_folder_list = &folderlist;
	
	error = gn_sms_delete(data, state);
	if (error != GN_ERR_NONE) {
		fprintf(stderr, "Deleting SMS failed! (%s)\n", gn_error_print(error));
	}
	
	return GN_ERR_NONE;
}

int startup() {
	setlocale(LC_ALL, "");
	bindtextdomain("waitsms", "");
	textdomain("waitsms");
	
	return 0;
}

int loop() {
	gn_error error;
	sig_t prev;
	
	prev = signal(SIGINT, SIG_DFL);
	
	/* Initialisation de gnokii */
	error = businit();
	
	if (error != GN_ERR_NONE) {
		fprintf(stderr, "startup(): %s\n", gn_error_print(error));
		return 1;
	}
	
	puts("Init OK");
	
	/* Initialisation de on_sms */
	data->on_sms = smsslave;
	data->callback_data = NULL;
	error = gn_sm_functions(GN_OP_OnSMS, data, state);
	
	if (error != GN_ERR_NONE) {
		fprintf(stderr, "loop(): %s\n", gn_error_print(error));
		return 1;
	}
	
	signal(SIGINT, prev);
	
	puts("Starting loop");
	
	prev = signal(SIGINT, sigint_handler);
	
	while (cont) {
		gn_sm_loop(1, state);
		error = gn_sm_functions(GN_OP_PollSMS, data, state);
	}
	
	signal(SIGINT, prev);
	
	return 0;
}
