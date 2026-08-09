package com.training;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class CertificateService {

    private final CertificateRepository repository;

    public CertificateService(CertificateRepository repository) {
        this.repository = repository;
    }

    public List<Certificate> findAll() {
        return repository.findAll();
    }

    public Certificate create(Certificate certificate) {
        return repository.save(certificate);
    }

    public Certificate findById(Long id) {
        return repository.findById(id);
    }
}
