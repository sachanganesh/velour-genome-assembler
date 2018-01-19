"""
	Sachandhan Ganesh
	Created On 10.18.2017

	Simple de novo genome assembler to test naive de Bruijn graph manipulation and the implications of
	read lengths, coverage, and kmer sizes.
"""

import argparse
import copy
from random import randint
from Bio import Seq, SeqIO, SeqRecord
from difflib import SequenceMatcher
import networkx as nx
from matplotlib import pyplot as plt
from pydot import graph_from_dot_data
from graphviz import Digraph


class VelourAssembler(object):
	def __init__(self, reads, read_len, k):
		self._k = k
		self._kmers = sorted(self.get_kmers(k, reads, read_len))
		self._graph = nx.DiGraph()
		self.build()


	@staticmethod
	def get_reads(seq, read_len, num_reads, k):
		reads = []

		for _ in range(num_reads):
			read = VelourAssembler.fragment_read(seq, read_len)
			if len(read) > k:
				reads.append(read)

		return reads

	@staticmethod
	def fragment_read(seq, frag_len):
		ind = randint(-frag_len / 2, len(seq) - 1)
		if (ind < 0):
			frag_len = frag_len + ind
			ind = 0

		if ind + frag_len >= len(seq):
			return seq[ind:]
		else:
			return seq[ind : ind + frag_len]


	@staticmethod
	def get_coverage(seq_len, reads, num_reads):
		avg_read_len = 0
		for read in reads:
			avg_read_len += len(read)
		avg_read_len /= len(reads)

		return num_reads * (avg_read_len / seq_len)


	def get_kmers(self, k, reads, read_len):
		kmer_set = set()

		for read in reads:
			if k > read_len:
				print("k for kmer is greater than read length")
				exit(1)
			elif k <= len(read):
				for i in range(len(read) - k + 1):
					kmer_set.add(read[i : i + k])

		return kmer_set


	def find_next_kmers(self, kmer):
		followers = []

		for other in self._kmers:
			if kmer is not other and kmer[1:] == other[:-1]:
				followers.append(other)

		return followers


	def build(self):
		for kmer in self._kmers:
			followers = self.find_next_kmers(kmer)
			self._graph.add_node(kmer)
			self._graph.add_edges_from([(kmer, fol) for fol in followers])


	def get_graph(self):
		return self._graph


	@staticmethod
	def remove_isolates(graph):
		isolates = list(nx.isolates(graph))
		graph.remove_nodes_from(isolates)


	def assemble(self):
		VelourAssembler.remove_isolates(self._graph)

		kmers = copy.deepcopy(self._graph.nodes())
		unresolved = 1

		while unresolved:
			graph_size = len(self._graph.nodes())

			for kmer in kmers:
				word = kmer

				while word is not None and word in self._graph:
					follower_parents = [self._graph.predecessors(w) for w in list(self._graph.successors(word))]

					if self._graph.out_degree(word) == 1 and len(follower_parents) is 1:
						follower = list(self._graph.successors(word))[0]

						# Overlap the words and get new joined word
						s = SequenceMatcher(None, follower, word)
						alpha, beta, overlap_len = s.find_longest_match(0, len(follower), 0, len(word))
						new_word = word[: beta + overlap_len] + follower[alpha + overlap_len:]

						# set new word in graph with appropriate chain
						self._graph.add_node(new_word)
						self._graph.add_edges_from([(new_word, child) for child in self._graph.successors(follower)])

						for parent in self._graph.predecessors(word):
							self._graph.add_edge(parent, new_word)

						# remove resolved nodes from graph
						self._graph.remove_node(word)
						self._graph.remove_node(follower)

						word = new_word
					else:
						word = None

			unresolved = graph_size - len(self._graph.nodes())


	def visualize_graph(self):
		nx.draw_spectral(self.get_graph(), with_labels=True, arrows=True)
		plt.show()


def parse_arguments():
	parser = argparse.ArgumentParser(description="Velour: Naive de novo genome assembler")
	parser.add_argument("-f", "--file", metavar=("filepath", "format"), nargs=2, type=str, help="DNA sequence source file as 'txt', 'fastq', or 'fasta'")
	parser.add_argument("read_len", metavar="L", type=int, help="length of reads")
	parser.add_argument("num_reads", metavar="N", type=int, help="number of reads")
	parser.add_argument("k", metavar="k", type=int, default=4, help="kmer length")
	parser.add_argument("-d", "--display", action="store_true", help="display pictoral results")

	args = parser.parse_args()
	return args


def main():
	args = parse_arguments()

	if args.file and args.file[1] == "txt":
		with open(args.file[0]) as seq_file:
			sample = seq_file.read().replace('\n', '').replace(' ', '')
	else:
		sample = "ATGGAAGTCGCGGAATC"

	reads = VelourAssembler.get_reads(sample, args.read_len, args.num_reads, args.k)

	coverage = VelourAssembler.get_coverage(len(sample), reads, args.num_reads)

	assembly = VelourAssembler(reads, args.read_len, args.k)

	print("Sequence:", sample)
	print("\nCoverage:", coverage)
	print("\nOriginal Kmers:")
	for node in assembly.get_graph().nodes():
		print("\t%s" % node)

	assembly.assemble()
	print("\nAssembled Contigs:")
	for node in assembly.get_graph().nodes():
		print("\t%s" % node)

	if args.display:
		assembly.visualize_graph()

if __name__ == "__main__":
	main()