package com.training;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/certificates")
public class CertificateController {

    private final CertificateService service;

    public CertificateController(CertificateService service) {
        this.service = service;
    }

    @GetMapping
    public List<Certificate> listCertificates() {
        return service.findAll();
    }

    @PostMapping
    public Certificate createCertificate(@RequestBody Certificate certificate) {
        return service.create(certificate);
    }

    @GetMapping("/{id}")
    public Certificate getCertificate(@PathVariable Long id) {
        return service.findById(id);
    }
}
