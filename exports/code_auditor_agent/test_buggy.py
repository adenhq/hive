
def insecure_function(user_input):
    # DANGEROUS: eval() can execute arbitrary code
    result = eval(user_input)
    
    # DANGEROUS: Open file with user provided path without validation
    f = open("/tmp/" + user_input, "w")
    f.write(str(result))
    f.close()
    return result
