package com.training;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TrainingService {

    private final TrainingRepository repository;

    public TrainingService(TrainingRepository repository) {
        this.repository = repository;
    }

    public List<Training> findAll() {
        return repository.findAll();
    }

    public void delete(Long id) {
        repository.deleteById(id);
    }
}
