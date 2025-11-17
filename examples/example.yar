rule DetectPasswordString {
    meta:
        description = "Detecta la palabra 'password' en ficheros"
    strings:
        $s1 = "password" nocase
    condition:
        $s1
}