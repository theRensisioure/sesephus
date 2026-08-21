import React from 'react';

const Sieve = () => {
  return (
    <div className="sieve-module animate-fade-in">
      <h2>Sieve Text Shredder</h2>
      <div className="glass-panel mt-6">
        <h3>Shredding Configuration</h3>
        <p className="mt-4 text-secondary">
          Configure the parsing rules and redaction thresholds for unstructured text ingestion.
        </p>
        <div className="mt-6 flex gap-4">
          <button className="btn">Load Corpus</button>
          <button className="btn btn-danger">Execute Purge</button>
        </div>
      </div>
    </div>
  );
};

export default Sieve;
