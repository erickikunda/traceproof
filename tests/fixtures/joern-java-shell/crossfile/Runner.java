class Runner { static Process run(String data) throws Exception {
    return Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", data});
} }
